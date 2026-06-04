<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import echo from './echo'

const email = ref('')
const password = ref('')

const usuarioActual = ref(null)
try {
  const raw = localStorage.getItem('usuario')
  usuarioActual.value = raw ? JSON.parse(raw) : null
} catch {
  localStorage.removeItem('usuario')
  usuarioActual.value = null
}

const esAdmin = computed(() => usuarioActual.value?.rol === 'admin')

const mensaje = ref('')
const mensajes = ref([])

// Admin
const usuarios = ref([])
const adminUsuarioIdDestino = ref(null)

const formMulta = ref({
  descripcion: '',
  monto: 0,
  detalles: '',
})

const formPago = ref({
  concepto: '',
  monto: 0,
  dias_atraso: 0,
  fecha_vencimiento: '',
  detalles: '',
})

const formAsamblea = ref({
  titulo: '',
  descripcion: '',
  fecha: '',
  lugar: '',
  agenda: '',
})

// Notificaciones
const notificaciones = ref([])
const mostrarPanel = ref(false)
const notificacionSeleccionada = ref(null)
const tiposIconos = {
  mensaje: '💬',
  multa: '💰',
  asamblea: '📅',
  pago_atrasado: '⚠️'
}

const tiposColores = {
  mensaje: '#4a90e2',
  multa: '#f5a623',
  asamblea: '#7ed321',
  pago_atrasado: '#d0021b'
}

const notificacionesNoLeidas = computed(() => 
  notificaciones.value.filter(n => !n.leida).length
)

// Estados HTTP: carga en botones + alerta con transición al resolver
const loading = ref({})
const alerta = ref({ visible: false, tipo: 'success', mensaje: '' })
let alertaTimer = null

const estaCargando = (key) => Boolean(loading.value[key])

const cerrarAlerta = () => {
  alerta.value.visible = false
  if (alertaTimer) {
    clearTimeout(alertaTimer)
    alertaTimer = null
  }
}

const mostrarAlerta = (tipo, mensaje) => {
  if (alertaTimer) clearTimeout(alertaTimer)
  alerta.value = { visible: true, tipo, mensaje }
  alertaTimer = setTimeout(cerrarAlerta, 5000)
}

const ejecutarPeticion = async (key, fn, { exito, error } = {}) => {
  if (loading.value[key]) return

  loading.value = { ...loading.value, [key]: true }
  try {
    const resultado = await fn()
    mostrarAlerta('success', exito || 'Operación completada correctamente')
    return resultado
  } catch (err) {
    const mensaje =
      error ||
      err?.response?.data?.error ||
      err?.response?.data?.message ||
      (err?.response?.status >= 500
        ? 'Error del servidor. Verifica que Laravel esté corriendo y la base de datos configurada.'
        : null) ||
      err?.message ||
      'No se pudo completar la solicitud'
    mostrarAlerta('error', mensaje)
  } finally {
    loading.value = { ...loading.value, [key]: false }
  }
}

const formatearHora = (fecha) => {
  if (!fecha) return ''
  const date = new Date(fecha)
  const horas = String(date.getHours()).padStart(2, '0')
  const minutos = String(date.getMinutes()).padStart(2, '0')
  return `${horas}:${minutos}`
}

const formatearFecha = (fecha) => {
  if (!fecha) return ''
  const date = new Date(fecha)
  return date.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const extraerNombre = (email) => {
  return email.split('@')[0]
}

const login = () =>
  ejecutarPeticion(
    'login',
    async () => {
      const response = await axios.post('http://127.0.0.1:8000/api/login', {
        correo: email.value.trim(),
        password: password.value,
      })

      if (!response.data?.ok || !response.data?.usuario) {
        throw new Error('Credenciales incorrectas')
      }

      const usuario = response.data.usuario
      localStorage.setItem('usuario', JSON.stringify(usuario))
      usuarioActual.value = usuario

      await Promise.all([
        cargarMensajes(),
        cargarNotificaciones(),
      ])
      escucharNotificaciones()
      if (usuario.rol === 'admin') {
        await cargarUsuarios()
      }
    },
    { exito: 'Sesión iniciada correctamente', error: 'Credenciales incorrectas' }
  )

const logout = () => {
  localStorage.removeItem('usuario')
  usuarioActual.value = null
  notificaciones.value = []
  mensajes.value = []
  usuarios.value = []
  adminUsuarioIdDestino.value = null
}

const cargarUsuarios = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:8000/api/usuarios')
    usuarios.value = response.data
    if (!adminUsuarioIdDestino.value && usuarios.value.length > 0) {
      const primerNoAdmin = usuarios.value.find(u => u.rol !== 'admin')
      adminUsuarioIdDestino.value = (primerNoAdmin || usuarios.value[0]).id
    }
  } catch (error) {
    console.error('Error cargando usuarios:', error)
  }
}

const crearMulta = () => {
  if (!esAdmin.value) return
  if (!adminUsuarioIdDestino.value) {
    mostrarAlerta('error', 'Selecciona un usuario destino')
    return
  }

  return ejecutarPeticion(
    'multa',
    async () => {
      await axios.post('http://127.0.0.1:8000/api/multas', {
        admin_id: usuarioActual.value.id,
        usuario_id: adminUsuarioIdDestino.value,
        descripcion: formMulta.value.descripcion,
        monto: Number(formMulta.value.monto),
        detalles: formMulta.value.detalles || null,
        estado: 'pendiente',
      })
      formMulta.value = { descripcion: '', monto: 0, detalles: '' }
    },
    { exito: 'Multa creada correctamente', error: 'No se pudo crear la multa' }
  )
}

const crearPagoAtrasado = () => {
  if (!esAdmin.value) return
  if (!adminUsuarioIdDestino.value) {
    mostrarAlerta('error', 'Selecciona un usuario destino')
    return
  }

  return ejecutarPeticion(
    'pago',
    async () => {
      await axios.post('http://127.0.0.1:8000/api/pagos-atrasados', {
        admin_id: usuarioActual.value.id,
        usuario_id: adminUsuarioIdDestino.value,
        concepto: formPago.value.concepto,
        monto: Number(formPago.value.monto),
        dias_atraso: Number(formPago.value.dias_atraso),
        fecha_vencimiento: formPago.value.fecha_vencimiento,
        detalles: formPago.value.detalles || null,
      })
      formPago.value = {
        concepto: '',
        monto: 0,
        dias_atraso: 0,
        fecha_vencimiento: '',
        detalles: '',
      }
    },
    {
      exito: 'Pago atrasado registrado correctamente',
      error: 'No se pudo crear el pago atrasado',
    }
  )
}

const crearAsamblea = () => {
  if (!esAdmin.value) return

  return ejecutarPeticion(
    'asamblea',
    async () => {
      await axios.post('http://127.0.0.1:8000/api/asambleas', {
        admin_id: usuarioActual.value.id,
        titulo: formAsamblea.value.titulo,
        descripcion: formAsamblea.value.descripcion,
        fecha: formAsamblea.value.fecha,
        lugar: formAsamblea.value.lugar,
        agenda: formAsamblea.value.agenda || null,
        estado: 'programada',
      })
      formAsamblea.value = {
        titulo: '',
        descripcion: '',
        fecha: '',
        lugar: '',
        agenda: '',
      }
    },
    { exito: 'Asamblea creada correctamente', error: 'No se pudo crear la asamblea' }
  )
}

const enviar = () => {
  if (!mensaje.value) return

  return ejecutarPeticion(
    'mensaje',
    async () => {
      await axios.post('http://127.0.0.1:8000/api/mensaje', {
        usuario: usuarioActual.value.correo,
        mensaje: mensaje.value,
      })
      mensaje.value = ''
    },
    { exito: 'Mensaje enviado', error: 'No se pudo enviar el mensaje' }
  )
}

const cargarMensajes = async () => {
  try {
    const response = await axios.get(
      'http://127.0.0.1:8000/api/mensajes'
    )
    mensajes.value = response.data
  } catch (error) {
    console.error('Error cargando mensajes:', error)
  }
}

const cargarNotificaciones = async () => {
  try {
    if (!usuarioActual.value) return
    
    const response = await axios.get(
      `http://127.0.0.1:8000/api/notificaciones/`,
      {
        params: { usuario_id: usuarioActual.value.id }
      }
    )
    notificaciones.value = response.data
  } catch (error) {
    console.error('Error cargando notificaciones:', error)
  }
}

const marcarComoLeida = (notificacion) =>
  ejecutarPeticion(
    `leida-${notificacion.id}`,
    async () => {
      await axios.put(
        `http://127.0.0.1:8000/api/notificaciones/${notificacion.id}/leida`
      )
      notificacion.leida = true
      notificacionSeleccionada.value = notificacion
    },
    {
      exito: 'Notificación marcada como leída',
      error: 'No se pudo marcar la notificación',
    }
  )

const verDetalles = (notificacion) => {
  if (!notificacion.leida) {
    marcarComoLeida(notificacion)
  }
  notificacionSeleccionada.value = notificacion
}

const cerrarDetalle = () => {
  notificacionSeleccionada.value = null
}

const escucharNotificaciones = () => {
  if (!usuarioActual.value) return

  // Los eventos del backend usan Channel público (no PrivateChannel)
  echo.channel(`usuario.${usuarioActual.value.id}`)
    .listen('.notificacion-nueva', (e) => {
      console.log('Nueva notificación:', e)
      cargarNotificaciones()
    })
    .listen('.multa-nueva', (e) => {
      console.log('Nueva multa:', e)
      cargarNotificaciones()
    })
    .listen('.pago-atrasado-nuevo', (e) => {
      console.log('Nuevo pago atrasado:', e)
      cargarNotificaciones()
    })

  echo.channel('asambleas')
    .listen('.asamblea-nueva', (e) => {
      console.log('Nueva asamblea:', e)
      cargarNotificaciones()
    })
}

onMounted(() => {
  if (usuarioActual.value) {
    cargarMensajes()
    cargarNotificaciones()
    escucharNotificaciones()
  }

  echo.channel('chat-channel')
    .listen('.nuevo-mensaje', (e) => {
      mensajes.value.push({
        usuario: e.usuario,
        mensaje: e.mensaje,
        created_at: e.created_at || new Date().toISOString()
      })
    })
})
</script>

<template>

<div class="app-root">

  <!-- LOGIN -->
  <div v-if="!usuarioActual" class="auth-shell">
    <div class="auth-backdrop" />
    <div class="auth-card">
      <div class="auth-logo">
        <div class="auth-logo-dot" />
      </div>
      <h1 class="auth-title">Bienvenido</h1>
      <p class="auth-subtitle">Inicia sesión en tu cuenta</p>

      <div class="auth-field">
        <label>Email</label>
        <input v-model="email" placeholder="admin@ejemplo.com" type="email" />
      </div>

      <div class="auth-field">
        <label>Contraseña</label>
        <input v-model="password" type="password" placeholder="••••••••" />
      </div>

      <div class="auth-row">
        <label class="auth-check">
          <input type="checkbox" disabled />
          <span>Recordarme</span>
        </label>
        <a class="auth-link" href="javascript:void(0)">¿Olvidaste tu contraseña?</a>
      </div>

      <button
        class="auth-btn"
        :disabled="estaCargando('login')"
        @click="login"
      >
        <Transition name="btn-swap" mode="out-in">
          <span v-if="estaCargando('login')" key="loading" class="btn-estado btn-estado--loading">
            <span class="spinner" aria-hidden="true" />
            Cargando...
          </span>
          <span v-else key="idle" class="btn-estado">Iniciar Sesión</span>
        </Transition>
      </button>

      <div class="auth-footnote">
        Sistema de Administración de Condominios v1.0
      </div>

      <div class="users">
        Demo: juan@gmail.com / maria@gmail.com / admin@gmail.com (password: 123)
      </div>
    </div>
  </div>

  <!-- APP -->
  <div v-else class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-title">CondoAdmin</div>
        <div class="brand-sub">Sistema de Gestión</div>
      </div>

      <nav class="nav">
        <a class="nav-item is-active" href="javascript:void(0)">
          <span class="nav-ico">▦</span>
          <span>Dashboard</span>
        </a>
        <a class="nav-item" href="javascript:void(0)">
          <span class="nav-ico">👥</span>
          <span>Residentes</span>
        </a>
        <a class="nav-item" href="javascript:void(0)">
          <span class="nav-ico">💬</span>
          <span>Mensajes</span>
        </a>
      </nav>

      <div class="sidebar-footer">
        <div class="sidebar-user">
          <div class="avatar">
            {{ (extraerNombre(usuarioActual.correo)?.[0] || 'U').toUpperCase() }}
          </div>
          <div class="sidebar-user-meta">
            <div class="sidebar-user-name">
              {{ esAdmin ? 'Administrador' : extraerNombre(usuarioActual.correo) }}
            </div>
            <div class="sidebar-user-mail">{{ usuarioActual.correo }}</div>
          </div>
        </div>
        <button class="sidebar-logout" @click="logout">Cerrar Sesión</button>
      </div>
    </aside>

    <main class="main">
      <div class="topbar">
        <div class="topbar-left">
          <div class="page-title">Dashboard</div>
          <div class="page-subtitle">Vista general del condominio</div>
        </div>

        <div class="topbar-right">
          <div class="search">
            <span class="search-ico">⌕</span>
            <input class="search-input" placeholder="Buscar..." />
          </div>

          <button class="topbar-icon-btn" @click="mostrarPanel = !mostrarPanel">
            <span class="bell-icon">🔔</span>
            <span v-if="notificacionesNoLeidas > 0" class="badge">
              {{ notificacionesNoLeidas }}
            </span>
          </button>
        </div>
      </div>

      <div class="content">
        <!-- Panel de administrador (mismo contenido, nuevo look) -->
        <div v-if="esAdmin" class="card admin-card-shell">
          <div class="card-head">
            <div>
              <div class="card-title">Administrador</div>
              <div class="card-subtitle">Acciones rápidas</div>
            </div>
            <div class="admin-user-select">
              <label>Residente</label>
              <select v-model="adminUsuarioIdDestino">
                <option v-for="u in usuarios" :key="u.id" :value="u.id">
                  {{ u.nombre }} ({{ u.correo }}) - {{ u.rol }}
                </option>
              </select>
            </div>
          </div>

          <div class="admin-grid">
            <div class="admin-card">
              <h4>Nueva multa</h4>
              <input v-model="formMulta.descripcion" placeholder="Descripción" />
              <input v-model="formMulta.monto" type="number" step="0.01" placeholder="Monto" />
              <input v-model="formMulta.detalles" placeholder="Detalles (opcional)" />
              <button
                class="admin-btn"
                :disabled="estaCargando('multa')"
                @click="crearMulta"
              >
                <Transition name="btn-swap" mode="out-in">
                  <span v-if="estaCargando('multa')" key="loading" class="btn-estado btn-estado--loading">
                    <span class="spinner" aria-hidden="true" />
                    Cargando...
                  </span>
                  <span v-else key="idle" class="btn-estado">Crear multa</span>
                </Transition>
              </button>
            </div>

            <div class="admin-card">
              <h4>Pago atrasado</h4>
              <input v-model="formPago.concepto" placeholder="Concepto" />
              <input v-model="formPago.monto" type="number" step="0.01" placeholder="Monto" />
              <input v-model="formPago.dias_atraso" type="number" placeholder="Días de atraso" />
              <input v-model="formPago.fecha_vencimiento" type="datetime-local" />
              <input v-model="formPago.detalles" placeholder="Detalles (opcional)" />
              <button
                class="admin-btn"
                :disabled="estaCargando('pago')"
                @click="crearPagoAtrasado"
              >
                <Transition name="btn-swap" mode="out-in">
                  <span v-if="estaCargando('pago')" key="loading" class="btn-estado btn-estado--loading">
                    <span class="spinner" aria-hidden="true" />
                    Cargando...
                  </span>
                  <span v-else key="idle" class="btn-estado">Crear pago atrasado</span>
                </Transition>
              </button>
            </div>

            <div class="admin-card">
              <h4>Asamblea</h4>
              <input v-model="formAsamblea.titulo" placeholder="Título" />
              <input v-model="formAsamblea.descripcion" placeholder="Descripción" />
              <input v-model="formAsamblea.fecha" type="datetime-local" />
              <input v-model="formAsamblea.lugar" placeholder="Lugar" />
              <input v-model="formAsamblea.agenda" placeholder="Agenda (opcional)" />
              <button
                class="admin-btn"
                :disabled="estaCargando('asamblea')"
                @click="crearAsamblea"
              >
                <Transition name="btn-swap" mode="out-in">
                  <span v-if="estaCargando('asamblea')" key="loading" class="btn-estado btn-estado--loading">
                    <span class="spinner" aria-hidden="true" />
                    Cargando...
                  </span>
                  <span v-else key="idle" class="btn-estado">Crear asamblea</span>
                </Transition>
              </button>
            </div>
          </div>
        </div>

        <!-- Mensajes (misma data, estilo tipo panel) -->
        <div class="card messages-shell">
          <div class="card-head">
            <div>
              <div class="card-title">Mensajes</div>
              <div class="card-subtitle">Conversación general</div>
            </div>
            <div class="chip">
              {{ extraerNombre(usuarioActual.correo) }}
              <span v-if="esAdmin" class="chip-dot">•</span>
            </div>
          </div>

          <div class="chat">
            <div
              v-for="(m, i) in mensajes"
              :key="i"
              :class="[
                'message-wrapper',
                m.usuario === usuarioActual.correo
                  ? 'mine'
                  : 'other'
              ]"
            >
              <div class="message">
                <div v-if="m.usuario !== usuarioActual.correo" class="sender-name">
                  {{ extraerNombre(m.usuario) }}
                </div>

                <div class="message-content">
                  {{ m.mensaje }}
                </div>

                <div class="message-time">
                  {{ formatearHora(m.created_at) }}
                </div>
              </div>
            </div>
          </div>

          <div class="input-area">
            <input
              v-model="mensaje"
              placeholder="Escribe un mensaje..."
              @keyup.enter="enviar"
            />

            <button
              class="send-btn"
              :disabled="estaCargando('mensaje')"
              @click="enviar"
            >
              <Transition name="btn-swap" mode="out-in">
                <span v-if="estaCargando('mensaje')" key="loading" class="btn-estado btn-estado--loading">
                  <span class="spinner spinner--light" aria-hidden="true" />
                </span>
                <span v-else key="idle" class="btn-estado">➤</span>
              </Transition>
            </button>
          </div>
        </div>
      </div>

    <!-- Panel de Notificaciones -->
    <div v-if="mostrarPanel" class="notifications-panel">
      <div class="panel-header">
        <h3>Notificaciones</h3>
        <button 
          class="close-panel"
          @click="mostrarPanel = false"
        >✕</button>
      </div>

      <div v-if="notificaciones.length === 0" class="empty-state">
        <p>No hay notificaciones</p>
      </div>

      <div v-else class="notifications-list">
        <div 
          v-for="notif in notificaciones" 
          :key="notif.id"
          :class="['notification-item', { 'no-leida': !notif.leida }]"
          @click="verDetalles(notif)"
        >
          <div class="notif-icon">
            {{ tiposIconos[notif.tipo] }}
          </div>
          <div class="notif-content">
            <div class="notif-titulo">{{ notif.titulo }}</div>
            <div class="notif-desc">{{ notif.descripcion }}</div>
            <div class="notif-time">{{ formatearHora(notif.created_at) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Detalle de Notificación -->
    <div v-if="notificacionSeleccionada" class="notification-detail-modal">
      <div class="modal-overlay" @click="cerrarDetalle"></div>
      <div class="modal-content">
        <div class="modal-header">
          <h2>
            <span class="icon">{{ tiposIconos[notificacionSeleccionada.tipo] }}</span>
            {{ notificacionSeleccionada.titulo }}
          </h2>
          <button class="close-btn" @click="cerrarDetalle">✕</button>
        </div>

        <div class="modal-body">
          <p class="modal-description">
            {{ notificacionSeleccionada.descripcion }}
          </p>
          <p class="modal-date">
            {{ formatearFecha(notificacionSeleccionada.created_at) }}
          </p>

          <!-- Detalles adicionales según tipo -->
          <div v-if="notificacionSeleccionada.detalles" class="modal-details">
            <div v-if="notificacionSeleccionada.tipo === 'multa'" class="detail-section">
              <h4>Información de Multa</h4>
              <p><strong>Monto:</strong> ${{ notificacionSeleccionada.detalles.monto }}</p>
              <p><strong>Estado:</strong> {{ notificacionSeleccionada.detalles.estado }}</p>
              <p v-if="notificacionSeleccionada.detalles.detalles"><strong>Detalles:</strong> {{ notificacionSeleccionada.detalles.detalles }}</p>
            </div>

            <div v-if="notificacionSeleccionada.tipo === 'asamblea'" class="detail-section">
              <h4>Detalles Asamblea</h4>
              <p><strong>Fecha:</strong> {{ formatearFecha(notificacionSeleccionada.detalles.fecha) }}</p>
              <p><strong>Lugar:</strong> {{ notificacionSeleccionada.detalles.lugar }}</p>
              <p v-if="notificacionSeleccionada.detalles.agenda"><strong>Agenda:</strong> {{ notificacionSeleccionada.detalles.agenda }}</p>
            </div>

            <div v-if="notificacionSeleccionada.tipo === 'pago_atrasado'" class="detail-section">
              <h4>Detalles del Pago</h4>
              <p><strong>Concepto:</strong> {{ notificacionSeleccionada.detalles.concepto }}</p>
              <p><strong>Monto:</strong> ${{ notificacionSeleccionada.detalles.monto }}</p>
              <p><strong>Días de Atraso:</strong> {{ notificacionSeleccionada.detalles.dias_atraso }}</p>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-primary" @click="cerrarDetalle">Cerrar</button>
        </div>
      </div>
    </div>
    </main>
  </div>

  <!-- Alerta global: resultado de la promesa HTTP -->
  <Transition name="alert-slide">
    <div
      v-if="alerta.visible"
      :class="['api-alerta', `api-alerta--${alerta.tipo}`]"
      role="alert"
    >
      <Transition name="alert-icon" mode="out-in">
        <span :key="alerta.tipo" class="api-alerta-ico">
          {{ alerta.tipo === 'success' ? '✓' : '!' }}
        </span>
      </Transition>
      <p class="api-alerta-texto">{{ alerta.mensaje }}</p>
      <button type="button" class="api-alerta-cerrar" @click="cerrarAlerta">✕</button>
    </div>
  </Transition>

</div>

</template>

<style>

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', sans-serif;
  background: #f3f4f6;
  color: #0f172a;
}

.app-root {
  min-height: 100vh;
}

/* Auth (login) */
.auth-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  position: relative;
  padding: 28px 18px;
}

.auth-backdrop {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(1200px 600px at 20% 30%, rgba(0,0,0,0.10), transparent 55%),
    radial-gradient(900px 500px at 70% 20%, rgba(0,0,0,0.10), transparent 60%),
    linear-gradient(180deg, rgba(0,0,0,0.28), rgba(0,0,0,0.28));
  filter: saturate(0.9);
}

.auth-shell::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(120deg, rgba(15, 23, 42, 0.25), rgba(15, 23, 42, 0.1)),
    radial-gradient(900px 600px at 60% 40%, rgba(255,255,255,0.10), transparent 55%);
  pointer-events: none;
}

.auth-card {
  position: relative;
  width: min(520px, 92vw);
  background: #ffffff;
  border-radius: 18px;
  padding: 34px 34px 26px;
  box-shadow: 0 30px 80px rgba(0,0,0,0.35);
}

.auth-logo {
  width: 44px;
  height: 44px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  margin: 0 auto 14px;
  background: #0b1220;
}

.auth-logo-dot {
  width: 16px;
  height: 16px;
  border-radius: 6px;
  background: linear-gradient(180deg, #9aa4b2, #5b6472);
}

.auth-title {
  margin: 0;
  text-align: center;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #0f172a;
}

.auth-subtitle {
  margin: 6px 0 20px;
  text-align: center;
  color: #64748b;
  font-size: 14px;
}

.auth-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 14px;
}

.auth-field label {
  font-size: 12px;
  color: #475569;
  font-weight: 700;
}

.auth-field input {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #ffffff;
  font-size: 14px;
  outline: none;
}

.auth-field input:focus {
  border-color: #0f172a;
  box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.12);
}

.auth-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 14px 0 18px;
}

.auth-check {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: #64748b;
  font-size: 13px;
}

.auth-check input {
  width: 14px;
  height: 14px;
}

.auth-link {
  color: #0f172a;
  font-size: 13px;
  text-decoration: none;
  opacity: 0.85;
}

.auth-link:hover {
  opacity: 1;
  text-decoration: underline;
}

.auth-btn {
  width: 100%;
  padding: 12px 14px;
  border: none;
  border-radius: 12px;
  background: #0b0b0b;
  color: #fff;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 12px 30px rgba(0,0,0,0.22);
}

.auth-btn:hover {
  background: #000;
}

.auth-footnote {
  margin-top: 16px;
  text-align: center;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.6);
}

.users {
  margin-top: 14px;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.6);
}

.shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 280px 1fr;
  background: #f3f4f6;
}

/* Sidebar */
.sidebar {
  background: #070707;
  color: #fff;
  display: flex;
  flex-direction: column;
  padding: 22px 18px;
  gap: 18px;
}

.brand-title {
  font-weight: 900;
  font-size: 18px;
  letter-spacing: -0.01em;
}

.brand-sub {
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.65;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 12px;
  border-radius: 12px;
  color: rgba(255,255,255,0.86);
  text-decoration: none;
  background: transparent;
}

.nav-item:hover {
  background: rgba(255,255,255,0.06);
}

.nav-item.is-active {
  background: rgba(255,255,255,0.10);
  color: #fff;
}

.nav-ico {
  width: 22px;
  text-align: center;
  opacity: 0.9;
}

.sidebar-footer {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sidebar-user {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 14px;
  background: rgba(255,255,255,0.06);
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  font-weight: 900;
  background: rgba(255,255,255,0.12);
}

.sidebar-user-name {
  font-weight: 800;
  font-size: 13px;
}

.sidebar-user-mail {
  font-size: 12px;
  opacity: 0.7;
}

.sidebar-logout {
  width: 100%;
  padding: 11px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.06);
  color: #fff;
  font-weight: 800;
  cursor: pointer;
}

.sidebar-logout:hover {
  background: rgba(255,255,255,0.10);
}

/* Main */
.main {
  padding: 26px 28px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 900;
  color: #0f172a;
}

.page-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  min-width: 260px;
}

.search-ico {
  opacity: 0.5;
}

.search-input {
  border: none;
  outline: none;
  width: 100%;
  font-size: 13px;
}

.topbar-icon-btn {
  position: relative;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #fff;
  cursor: pointer;
  display: grid;
  place-items: center;
}

.topbar-icon-btn:hover {
  background: #f8fafc;
}

.content {
  margin-top: 18px;
  display: grid;
  gap: 14px;
}

.card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  box-shadow: 0 10px 35px rgba(15,23,42,0.05);
  overflow: hidden;
}

.card-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border-bottom: 1px solid #eef2f7;
}

.card-title {
  font-weight: 900;
  color: #0f172a;
}

.card-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  font-size: 12px;
  color: #334155;
  background: #fff;
}

.chip-dot {
  opacity: 0.6;
}

.admin-card-shell .admin-user-select {
  min-width: 320px;
}

.admin-user-select label {
  font-size: 12px;
  color: #64748b;
  font-weight: 800;
  margin-bottom: 6px;
  display: block;
}

.admin-user-select select {
  width: 100%;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #fff;
}

.admin-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 14px 14px 16px;
}

.admin-card {
  border: 1px solid #eef2f7;
  background: #fbfbfb;
  border-radius: 14px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.admin-card h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 900;
  color: #0f172a;
}

.admin-card input {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #fff;
  font-size: 13px;
}

.admin-btn {
  padding: 10px 12px;
  border-radius: 12px;
  border: none;
  background: #0b0b0b;
  color: #fff;
  font-weight: 900;
  cursor: pointer;
}

.admin-btn:hover {
  background: #000;
}

.messages-shell .chat {
  height: 52vh;
  max-height: 520px;
}

.badge {
  position: absolute;
  top: -8px;
  right: -8px;
  background: #d0021b;
  color: white;
  border-radius: 999px;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  display: grid;
  place-items: center;
  font-size: 0.72rem;
  font-weight: 900;
  border: 2px solid #f3f4f6;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.notifications-btn {
  position: relative;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  display: grid;
  place-items: center;
  transition: all 0.3s ease;
}

.notifications-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.05);
}

.badge {
  position: absolute;
  top: -8px;
  right: -8px;
  background: #d0021b;
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  font-size: 0.75rem;
  font-weight: bold;
  border: 2px solid #1a1a1a;
}

.logout-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  display: grid;
  place-items: center;
  transition: all 0.3s ease;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.05);
}

.notifications-panel {
  position: absolute;
  top: 86px;
  right: 28px;
  width: 360px;
  max-height: 600px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  z-index: 100;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.close-panel {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  padding: 0;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  transition: all 0.3s;
}

.close-panel:hover {
  background: #f0f0f0;
}

.notifications-list {
  flex: 1;
  overflow-y: auto;
}

.notification-item {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: all 0.3s;
  background: #fafafa;
}

.notification-item:hover {
  background: #f0f0f0;
}

.notification-item.no-leida {
  background: #f3f9ff;
  font-weight: 600;
}

.notif-icon {
  font-size: 1.5rem;
  min-width: 40px;
  text-align: center;
}

.notif-content {
  flex: 1;
  min-width: 0;
}

.notif-titulo {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 4px;
  color: #1a1a1a;
}

.notif-desc {
  font-size: 0.8rem;
  color: #666;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notif-time {
  font-size: 0.7rem;
  color: #999;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #999;
}

.notification-detail-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  cursor: pointer;
}

.modal-content {
  position: relative;
  background: white;
  border-radius: 20px;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    transform: translateY(50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  padding: 20px 24px;
  border-bottom: 1px solid #eee;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.3rem;
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-header .icon {
  font-size: 1.8rem;
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.5rem;
  padding: 0;
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
}

.modal-body {
  padding: 24px;
}

.modal-description {
  font-size: 1rem;
  color: #333;
  line-height: 1.6;
  margin: 0 0 12px;
}

.modal-date {
  font-size: 0.85rem;
  color: #999;
  margin: 0 0 20px;
}

.modal-details {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.detail-section {
  margin-bottom: 20px;
}

.detail-section h4 {
  margin: 0 0 12px;
  font-size: 0.95rem;
  color: #1a1a1a;
  font-weight: 600;
}

.detail-section p {
  margin: 8px 0;
  font-size: 0.9rem;
  color: #555;
}

.modal-footer {
  padding: 20px 24px;
  border-top: 1px solid #eee;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-primary {
  padding: 10px 24px;
  background: #1a1a1a;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s;
}

.btn-primary:hover {
  background: #000;
}


.chat {
  flex: 1;
  overflow-y: auto;
  padding: 18px 18px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat::-webkit-scrollbar {
  width: 6px;
}

.chat::-webkit-scrollbar-track {
  background: transparent;
}

.chat::-webkit-scrollbar-thumb {
  background: #ddd;
  border-radius: 3px;
}

.chat::-webkit-scrollbar-thumb:hover {
  background: #999;
}

.message-wrapper {
  display: flex;
  margin-bottom: 8px;
}

.mine {
  justify-content: flex-end;
}

.other {
  justify-content: flex-start;
}

.message {
  max-width: 320px;
  padding: 12px 16px;
  border-radius: 18px;
  word-wrap: break-word;
  line-height: 1.4;
}

.mine .message {
  background: #0b0b0b;
  color: white;
  box-shadow: 0 2px 8px rgba(26, 26, 26, 0.12);
}

.other .message {
  background: #f0f0f0;
  color: #1a1a1a;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.sender-name {
  display: block;
  font-size: 0.75rem;
  opacity: 0.7;
  margin-bottom: 4px;
  font-weight: 600;
}

.message-content {
  margin: 0;
  font-size: 0.95rem;
}

.message-time {
  font-size: 0.7rem;
  opacity: 0.6;
  margin-top: 4px;
  text-align: right;
}

.mine .message-time {
  opacity: 0.5;
}

.input-area {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 14px 18px 16px;
  background: #ffffff;
  border-top: 1px solid #eef2f7;
}

.input-area input {
  flex: 1;
  padding: 12px 16px;
  border-radius: 24px;
  border: 1px solid #ddd;
  background: #f9f9f9;
  font-size: 0.95rem;
  resize: none;
  max-height: 100px;
  font-family: inherit;
}

.input-area input:focus {
  outline: none;
  border-color: #1a1a1a;
  background: #ffffff;
}

.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #0b0b0b;
  color: white;
  border: none;
  cursor: pointer;
  display: grid;
  place-items: center;
  font-size: 1.1rem;
  transition: all 0.3s ease;
}

.send-btn:hover {
  background: #000000;
  transform: scale(1.05);
}

/* Transiciones Vue: botones HTTP (enter/leave) */
.btn-estado {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-estado--loading {
  opacity: 0.95;
}

.btn-swap-enter-active,
.btn-swap-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.btn-swap-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.btn-swap-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(15, 23, 42, 0.15);
  border-top-color: #0f172a;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.spinner--light {
  border-color: rgba(255, 255, 255, 0.25);
  border-top-color: #fff;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.auth-btn:disabled,
.admin-btn:disabled,
.send-btn:disabled {
  opacity: 0.72;
  cursor: not-allowed;
  transform: none;
}

/* Transiciones Vue: alerta resultado promesa */
.api-alerta {
  position: fixed;
  top: 22px;
  right: 22px;
  z-index: 9999;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 280px;
  max-width: min(420px, calc(100vw - 40px));
  padding: 14px 16px;
  border-radius: 14px;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.18);
  border: 1px solid transparent;
}

.api-alerta--success {
  background: #ecfdf5;
  border-color: #a7f3d0;
  color: #065f46;
}

.api-alerta--error {
  background: #fef2f2;
  border-color: #fecaca;
  color: #991b1b;
}

.api-alerta-ico {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  font-weight: 900;
  flex-shrink: 0;
}

.api-alerta--success .api-alerta-ico {
  background: #10b981;
  color: #fff;
}

.api-alerta--error .api-alerta-ico {
  background: #ef4444;
  color: #fff;
}

.api-alerta-texto {
  margin: 0;
  flex: 1;
  font-size: 14px;
  line-height: 1.45;
  font-weight: 600;
  padding-top: 4px;
}

.api-alerta-cerrar {
  border: none;
  background: transparent;
  cursor: pointer;
  opacity: 0.55;
  font-size: 14px;
  padding: 2px 4px;
}

.api-alerta-cerrar:hover {
  opacity: 1;
}

.alert-slide-enter-active,
.alert-slide-leave-active {
  transition: opacity 0.35s ease, transform 0.35s ease;
}

.alert-slide-enter-from,
.alert-slide-leave-to {
  opacity: 0;
  transform: translateY(-14px) scale(0.96);
}

.alert-slide-enter-to,
.alert-slide-leave-from {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.alert-icon-enter-active,
.alert-icon-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.alert-icon-enter-from,
.alert-icon-leave-to {
  opacity: 0;
  transform: scale(0.6);
}

@media (max-width: 768px) {
  .shell {
    grid-template-columns: 1fr;
  }

  .api-alerta {
    left: 16px;
    right: 16px;
    min-width: auto;
  }

  .sidebar {
    display: none;
  }

  .main {
    padding: 18px 16px;
  }

  .search {
    min-width: 180px;
  }

  .admin-grid {
    grid-template-columns: 1fr;
  }

  .message {
    max-width: 85vw;
  }
}

</style>