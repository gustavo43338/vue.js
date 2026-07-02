<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import api, { guardarSesion, limpiarSesion, obtenerToken } from './api'
import echo from './echo'

const email = ref('')
const password = ref('')
const forgotStep = ref('none')
const forgotEmail = ref('')
const forgotCodeDigits = ref(Array.from({ length: 6 }, () => ''))
const forgotNewPassword = ref('')
const forgotConfirmPassword = ref('')
const forgotDebugCode = ref('')
const codeInputs = ref([])

const forgotCode = computed({
  get: () => forgotCodeDigits.value.join(''),
  set: (value) => {
    const digits = String(value).replace(/\D/g, '').slice(0, 6).split('')
    forgotCodeDigits.value = Array.from({ length: 6 }, (_, index) => digits[index] || '')
  },
})

const usuarioActual = ref(null)
try {
  const raw = localStorage.getItem('usuario')
  usuarioActual.value = raw ? JSON.parse(raw) : null
} catch {
  localStorage.removeItem('usuario')
  usuarioActual.value = null
}

const esAdmin = computed(() => usuarioActual.value?.rol === 'admin')

const vistaActual = ref('dashboard')
const buscarResidente = ref('')
const formUsuario = ref({
  id: null,
  nombre: '',
  correo: '',
  password: '',
  rol: 'usuario',
})

const pendienteVerificacion = ref(false)
const correoPendiente = ref('')

const residentesFiltrados = computed(() => {
  const q = buscarResidente.value.trim().toLowerCase()
  return usuarios.value.filter((u) => {
    if (u.rol === 'admin') return false
    if (!q) return true
    return (
      u.nombre?.toLowerCase().includes(q) ||
      u.correo?.toLowerCase().includes(q)
    )
  })
})

const tituloVista = computed(() => {
  if (vistaActual.value === 'residentes') return 'Residentes'
  if (vistaActual.value === 'mensajes') return 'Mensajes'
  return esAdmin.value ? 'Panel de Administración' : 'Dashboard'
})

const subtituloVista = computed(() => {
  if (vistaActual.value === 'residentes') return 'Gestiona la información de los residentes'
  if (vistaActual.value === 'mensajes') return 'Conversación general del condominio'
  return esAdmin.value
    ? 'Condominio — multas, pagos y asambleas'
    : 'Vista general del condominio'
})

const cambiarVista = (vista) => {
  vistaActual.value = vista
}

const iniciales = (nombre) => {
  if (!nombre) return '?'
  return nombre
    .split(' ')
    .map((p) => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

const estaVerificado = (u) => Boolean(u.email_verified_at)

const abrirFormUsuario = (usuario = null) => {
  if (usuario) {
    formUsuario.value = {
      id: usuario.id,
      nombre: usuario.nombre,
      correo: usuario.correo,
      password: '',
      rol: usuario.rol,
    }
  } else {
    formUsuario.value = {
      id: null,
      nombre: '',
      correo: '',
      password: '',
      rol: 'usuario',
    }
  }
  abrirModal('usuario')
}

const guardarUsuario = () => {
  if (!formUsuario.value.nombre || !formUsuario.value.correo) {
    mostrarAlerta('error', 'Nombre y correo son obligatorios')
    return
  }
  if (!formUsuario.value.id && !formUsuario.value.password) {
    mostrarAlerta('error', 'La contraseña es obligatoria para nuevos usuarios')
    return
  }

  const esEdicion = Boolean(formUsuario.value.id)
  const key = esEdicion ? `usuario-edit-${formUsuario.value.id}` : 'usuario-create'

  return ejecutarPeticion(
    key,
    async () => {
      const payload = {
        nombre: formUsuario.value.nombre,
        correo: formUsuario.value.correo,
        rol: formUsuario.value.rol,
      }
      if (formUsuario.value.password) {
        payload.password = formUsuario.value.password
      }

      if (esEdicion) {
        await api.put(`/usuarios/${formUsuario.value.id}`, payload)
        agregarHistorial(
          'mensaje',
          'Residente actualizado',
          `${formUsuario.value.nombre} (${formUsuario.value.correo})`
        )
      } else {
        await api.post('/usuarios', { ...payload, password: formUsuario.value.password })
        agregarHistorial(
          'mensaje',
          'Usuario registrado',
          `${formUsuario.value.nombre} — correo de verificación enviado`
        )
      }

      cerrarModal()
      await cargarUsuarios()
    },
    {
      exito: esEdicion ? 'Usuario actualizado' : 'Usuario creado. Se envió correo de verificación.',
      error: 'No se pudo guardar el usuario',
    }
  )
}

const eliminarUsuario = (usuario) => {
  if (!confirm(`¿Eliminar a ${usuario.nombre}?`)) return

  return ejecutarPeticion(
    `usuario-del-${usuario.id}`,
    async () => {
      await api.delete(`/usuarios/${usuario.id}`)
      agregarHistorial('mensaje', 'Usuario eliminado', usuario.nombre)
      await cargarUsuarios()
    },
    { exito: 'Usuario eliminado', error: 'No se pudo eliminar' }
  )
}

const reenviarVerificacion = (usuario) =>
  ejecutarPeticion(
    `verif-${usuario.id}`,
    async () => {
      await api.post(`/usuarios/${usuario.id}/reenviar-verificacion`)
    },
    { exito: `Correo reenviado a ${usuario.correo}`, error: 'No se pudo reenviar' }
  )

const mensaje = ref('')
const mensajes = ref([])

// Admin
const usuarios = ref([])
const adminUsuarioIdDestino = ref(null)

const formMulta = ref({
  descripcion: '',
  monto: 0,
  detalles: '',
  estado: 'pendiente',
  fecha_vencimiento: '',
})

const modalActivo = ref(null)
const multasLista = ref([])
const historial = ref([])

const abrirModal = (tipo) => {
  modalActivo.value = tipo
}

const cerrarModal = () => {
  modalActivo.value = null
}

const agregarHistorial = (tipo, titulo, subtitulo) => {
  const entrada = {
    id: Date.now(),
    tipo,
    titulo,
    subtitulo,
    fecha: new Date().toISOString(),
  }
  historial.value = [entrada, ...historial.value].slice(0, 40)
  localStorage.setItem('admin_historial', JSON.stringify(historial.value))
}

const cargarHistorial = () => {
  try {
    const raw = localStorage.getItem('admin_historial')
    historial.value = raw ? JSON.parse(raw) : []
  } catch {
    historial.value = []
  }
}

const haceCuanto = (fecha) => {
  if (!fecha) return ''
  const diff = Date.now() - new Date(fecha).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Hace un momento'
  if (mins < 60) return `Hace ${mins} min`
  const horas = Math.floor(mins / 60)
  if (horas < 24) return `Hace ${horas} h`
  const dias = Math.floor(horas / 24)
  return `Hace ${dias} d`
}

const nombreResidente = (usuarioId) => {
  const u = usuarios.value.find((x) => x.id === usuarioId)
  return u?.nombre || `Residente #${usuarioId}`
}

const cargarMultasAdmin = async () => {
  if (!esAdmin.value) return
  const residentes = usuarios.value.filter((u) => u.rol !== 'admin')
  const todas = []
  for (const u of residentes) {
    try {
      const { data } = await api.get(`/multas/usuario/${u.id}`)
      data.forEach((m) =>
        todas.push({
          ...m,
          residente_nombre: u.nombre,
          residente_correo: u.correo,
        })
      )
    } catch (e) {
      console.error('Error cargando multas:', e)
    }
  }
  multasLista.value = todas.sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  )
}

const resetFormMulta = () => {
  formMulta.value = {
    descripcion: '',
    monto: 0,
    detalles: '',
    estado: 'pendiente',
    fecha_vencimiento: '',
  }
}

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
    if (err?.response?.status === 401) {
      await logout()
      mostrarAlerta('error', 'Sesión expirada. Inicia sesión nuevamente.')
      return
    }

    const validationErrors = err?.response?.data?.errors
      ? Object.values(err.response.data.errors).flat().join(' ')
      : null

    const mensaje =
      error ||
      validationErrors ||
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

const login = () => {
  pendienteVerificacion.value = false
  return ejecutarPeticion(
    'login',
    async () => {
      try {
        const response = await api.post('/login', {
          correo: email.value.trim(),
          password: password.value,
        })

        if (!response.data?.ok || !response.data?.token) {
          throw new Error('Credenciales incorrectas')
        }

        guardarSesion(response.data.token, response.data.usuario)
        usuarioActual.value = response.data.usuario

        await Promise.all([cargarMensajes(), cargarNotificaciones()])
        escucharNotificaciones()
        if (response.data.usuario.rol === 'admin') {
          await cargarUsuarios()
          cargarHistorial()
          await cargarMultasAdmin()
        }
      } catch (err) {
        if (err.response?.data?.requiere_verificacion) {
          pendienteVerificacion.value = true
          correoPendiente.value = err.response.data.correo || email.value
        }
        throw err
      }
    },
    { exito: 'Sesión iniciada correctamente', error: 'Credenciales incorrectas' }
  )
}

const iniciarRecuperacion = () => {
  forgotStep.value = 'request'
  forgotEmail.value = email.value.trim()
  forgotCodeDigits.value = Array.from({ length: 6 }, () => '')
  forgotNewPassword.value = ''
  forgotConfirmPassword.value = ''
}

const cancelarRecuperacion = () => {
  forgotStep.value = 'none'
  forgotEmail.value = ''
  forgotCodeDigits.value = Array.from({ length: 6 }, () => '')
  forgotNewPassword.value = ''
  forgotConfirmPassword.value = ''
}

const focusCodeInput = (index) => {
  nextTick(() => {
    const input = codeInputs.value?.[index]
    if (input && typeof input.focus === 'function') {
      input.focus()
    }
  })
}

const handleCodeInput = (event, index) => {
  const value = String(event.target.value).replace(/\D/g, '').slice(0, 1)
  forgotCodeDigits.value[index] = value
  if (value && index < 5) {
    focusCodeInput(index + 1)
  }
}

const handleCodeKeydown = (event, index) => {
  if (event.key === 'Backspace') {
    if (forgotCodeDigits.value[index]) {
      forgotCodeDigits.value[index] = ''
    } else if (index > 0) {
      forgotCodeDigits.value[index - 1] = ''
      focusCodeInput(index - 1)
    }
  }
}

const handleCodePaste = (event) => {
  const pasted = (event.clipboardData.getData('text') || '').replace(/\D/g, '').slice(0, 6)
  forgotCodeDigits.value = Array.from({ length: 6 }, (_, index) => pasted[index] || '')
  if (pasted.length < 6) {
    focusCodeInput(pasted.length)
  }
}

const enviarCodigoRecuperacion = () => {
  const correo = forgotEmail.value.trim()
  if (!correo) {
    mostrarAlerta('error', 'Ingresa tu correo para recuperar tu contraseña')
    return
  }

  forgotDebugCode.value = ''

  return ejecutarPeticion(
    'forgotPassword',
    async () => {
      const response = await api.post('/password/forgot', { correo })
      forgotDebugCode.value = response.data?.debug_code || ''
    },
    {
      exito: 'Te enviamos un código al correo. Revisa tu bandeja de entrada.',
      error: 'No se pudo enviar el correo de recuperación',
    }
  ).then(() => {
    forgotStep.value = 'reset'
  })
}

const restablecerContrasena = () => {
  const correo = forgotEmail.value.trim()
  const codigo = forgotCode.value.trim()
  const nueva = forgotNewPassword.value
  const confirmar = forgotConfirmPassword.value

  if (!correo || !codigo || !nueva || !confirmar) {
    mostrarAlerta('error', 'Completa todos los campos para restablecer tu contraseña')
    return
  }

  if (nueva !== confirmar) {
    mostrarAlerta('error', 'Las contraseñas no coinciden')
    return
  }

  return ejecutarPeticion(
    'resetPassword',
    async () => {
      await api.post('/password/reset', {
        correo,
        code: codigo,
        password: nueva,
        password_confirmation: confirmar,
      })
    },
    {
      exito: 'Contraseña restablecida correctamente. Ya puedes iniciar sesión.',
      error: 'No se pudo restablecer la contraseña',
    }
  ).then(() => {
    cancelarRecuperacion()
    email.value = correo
    password.value = ''
  })
}

const logout = async () => {
  try {
    if (obtenerToken()) await api.post('/logout')
  } catch {
    /* ignorar */
  }
  limpiarSesion()
  usuarioActual.value = null
  notificaciones.value = []
  mensajes.value = []
  usuarios.value = []
  adminUsuarioIdDestino.value = null
  multasLista.value = []
  modalActivo.value = null
  vistaActual.value = 'dashboard'
  pendienteVerificacion.value = false
}

const cargarUsuarios = async () => {
  try {
    const response = await api.get('/usuarios')
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
      await api.post('/multas', {
        usuario_id: adminUsuarioIdDestino.value,
        descripcion: formMulta.value.descripcion,
        monto: Number(formMulta.value.monto),
        detalles: formMulta.value.detalles || null,
        estado: formMulta.value.estado,
        fecha_vencimiento: formMulta.value.fecha_vencimiento || null,
      })
      const residente = nombreResidente(adminUsuarioIdDestino.value)
      agregarHistorial(
        'multa',
        'Multa registrada',
        `${residente} — ${formMulta.value.descripcion} ($${Number(formMulta.value.monto).toFixed(2)})`
      )
      resetFormMulta()
      cerrarModal()
      await cargarMultasAdmin()
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
      await api.post('/pagos-atrasados', {
        usuario_id: adminUsuarioIdDestino.value,
        concepto: formPago.value.concepto,
        monto: Number(formPago.value.monto),
        dias_atraso: Number(formPago.value.dias_atraso),
        fecha_vencimiento: formPago.value.fecha_vencimiento,
        detalles: formPago.value.detalles || null,
      })
      const residente = nombreResidente(adminUsuarioIdDestino.value)
      agregarHistorial(
        'pago_atrasado',
        'Pago atrasado registrado',
        `${residente} — ${formPago.value.concepto} (${formPago.value.dias_atraso} días)`
      )
      formPago.value = {
        concepto: '',
        monto: 0,
        dias_atraso: 0,
        fecha_vencimiento: '',
        detalles: '',
      }
      cerrarModal()
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
      await api.post('/asambleas', {
        titulo: formAsamblea.value.titulo,
        descripcion: formAsamblea.value.descripcion,
        fecha: formAsamblea.value.fecha,
        lugar: formAsamblea.value.lugar,
        agenda: formAsamblea.value.agenda || null,
        estado: 'programada',
      })
      const tituloAsm = formAsamblea.value.titulo
      const lugarAsm = formAsamblea.value.lugar
      formAsamblea.value = {
        titulo: '',
        descripcion: '',
        fecha: '',
        lugar: '',
        agenda: '',
      }
      agregarHistorial(
        'asamblea',
        'Asamblea programada',
        `${tituloAsm} — ${lugarAsm}`
      )
      cerrarModal()
    },
    { exito: 'Asamblea creada correctamente', error: 'No se pudo crear la asamblea' }
  )
}

const enviar = () => {
  if (!mensaje.value) return

  return ejecutarPeticion(
    'mensaje',
    async () => {
      await api.post('/mensaje', {
        mensaje: mensaje.value,
      })
      mensaje.value = ''
    },
    { exito: 'Mensaje enviado', error: 'No se pudo enviar el mensaje' }
  )
}

const cargarMensajes = async () => {
  try {
    const response = await api.get('/mensajes')
    mensajes.value = response.data
  } catch (error) {
    console.error('Error cargando mensajes:', error)
  }
}

const cargarNotificaciones = async () => {
  try {
    if (!usuarioActual.value) return
    
    const response = await api.get('/notificaciones/', {
      params: { usuario_id: usuarioActual.value.id },
    })
    notificaciones.value = response.data
  } catch (error) {
    console.error('Error cargando notificaciones:', error)
  }
}

const marcarComoLeida = (notificacion) =>
  ejecutarPeticion(
    `leida-${notificacion.id}`,
    async () => {
      await api.put(`/notificaciones/${notificacion.id}/leida`)
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

onMounted(async () => {
  const params = new URLSearchParams(window.location.search)
  if (params.get('correo_verificado') === '1') {
    mostrarAlerta('success', '¡Correo verificado! Ya puedes iniciar sesión.')
    window.history.replaceState({}, '', window.location.pathname)
  }

  if (usuarioActual.value && obtenerToken()) {
    try {
      const { data } = await api.get('/me')
      usuarioActual.value = data.usuario
      guardarSesion(obtenerToken(), data.usuario)
    } catch {
      await logout()
      return
    }

    cargarMensajes()
    cargarNotificaciones()
    escucharNotificaciones()
    if (usuarioActual.value.rol === 'admin') {
      await cargarUsuarios()
      cargarHistorial()
      await cargarMultasAdmin()
    }
  } else if (usuarioActual.value && !obtenerToken()) {
    await logout()
  }

  window.addEventListener('session-expired', async () => {
    await logout()
  })

  echo.channel('chat-channel')
    .listen('.nuevo-mensaje', (e) => {
      mensajes.value.push({
        usuario: e.usuario,
        mensaje: e.mensaje,
        created_at: e.created_at || new Date().toISOString(),
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
        <span class="auth-logo-icon">🏢</span>
      </div>
      <h1 class="auth-title">Bienvenido</h1>
      <p class="auth-subtitle">Inicia sesión en tu cuenta</p>

      <template v-if="forgotStep === 'none'">
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
          <a class="auth-link" href="javascript:void(0)" @click="iniciarRecuperacion">¿Olvidaste tu contraseña?</a>
        </div>
      </template>

      <div v-if="forgotStep !== 'none'" class="auth-recovery">
        <div class="auth-recovery-header">
          <h2>Recuperar contraseña</h2>
          <p>Ingresa tu correo y el código que recibirás para crear una nueva contraseña.</p>
        </div>
        <div class="auth-field">
          <label>Correo de recuperación</label>
          <input v-model="forgotEmail" type="email" placeholder="correo@ejemplo.com" />
        </div>
        <button
          class="auth-btn"
          :disabled="estaCargando('forgotPassword')"
          @click="enviarCodigoRecuperacion"
        >
          <Transition name="btn-swap" mode="out-in">
            <span v-if="estaCargando('forgotPassword')" key="loading" class="btn-estado btn-estado--loading">
              <span class="spinner" aria-hidden="true" />
              Enviando código...
            </span>
            <span v-else key="idle" class="btn-estado">Enviar código de verificación</span>
          </Transition>
        </button>

        <div v-if="forgotStep === 'reset'">
          <div v-if="forgotDebugCode" class="auth-field auth-field--debug">
            <label>Código temporal</label>
            <div class="debug-code-box">{{ forgotDebugCode }}</div>
            <p class="debug-help">El código solo se muestra en desarrollo cuando el correo no puede entregarse.</p>
          </div>
          <div class="auth-field auth-field--code">
            <label>Código de verificación</label>
            <div class="auth-code-grid">
              <input
                v-for="(digit, index) in forgotCodeDigits"
                :key="index"
                ref="codeInputs"
                class="auth-code-digit"
                type="text"
                inputmode="numeric"
                pattern="[0-9]*"
                maxlength="1"
                :value="digit"
                @input="handleCodeInput($event, index)"
                @keydown="handleCodeKeydown($event, index)"
                @paste.prevent="handleCodePaste($event)"
                autocomplete="one-time-code"
                placeholder="•"
              />
            </div>
          </div>
          <div class="auth-field">
            <label>Nueva contraseña</label>
            <input v-model="forgotNewPassword" type="password" placeholder="••••••••" />
          </div>
          <div class="auth-field">
            <label>Confirmar contraseña</label>
            <input v-model="forgotConfirmPassword" type="password" placeholder="••••••••" />
          </div>
          <button
            class="auth-btn"
            :disabled="estaCargando('resetPassword')"
            @click="restablecerContrasena"
          >
            <Transition name="btn-swap" mode="out-in">
              <span v-if="estaCargando('resetPassword')" key="loading" class="btn-estado btn-estado--loading">
                <span class="spinner" aria-hidden="true" />
                Restableciendo...
              </span>
              <span v-else key="idle" class="btn-estado">Restablecer contraseña</span>
            </Transition>
          </button>
        </div>

        <button type="button" class="btn-ghost" @click="cancelarRecuperacion">Volver al login</button>
      </div>

      <button
        v-if="forgotStep === 'none'"
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

      <Transition name="alert-slide">
        <div v-if="pendienteVerificacion" class="auth-verify-banner">
          <p>
            Debes verificar <strong>{{ correoPendiente }}</strong> antes de entrar.
            Revisa tu bandeja de entrada (y spam).
          </p>
        </div>
      </Transition>
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
        <a
          class="nav-item"
          :class="{ 'is-active': vistaActual === 'dashboard' }"
          href="javascript:void(0)"
          @click="cambiarVista('dashboard')"
        >
          <span class="nav-ico">▦</span>
          <span>Dashboard</span>
        </a>
        <a
          v-if="esAdmin"
          class="nav-item"
          :class="{ 'is-active': vistaActual === 'residentes' }"
          href="javascript:void(0)"
          @click="cambiarVista('residentes')"
        >
          <span class="nav-ico">👥</span>
          <span>Residentes</span>
        </a>
        <a
          class="nav-item"
          :class="{ 'is-active': vistaActual === 'mensajes' }"
          href="javascript:void(0)"
          @click="cambiarVista('mensajes')"
        >
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
          <div class="page-title">{{ tituloVista }}</div>
          <div class="page-subtitle">{{ subtituloVista }}</div>
        </div>

        <div class="topbar-right">
          <div v-if="vistaActual === 'residentes'" class="search">
            <span class="search-ico">⌕</span>
            <input
              v-model="buscarResidente"
              class="search-input"
              placeholder="Buscar por nombre o correo..."
            />
          </div>
          <div v-else class="search">
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
        <!-- Vista Residentes (solo admin) -->
        <div v-if="esAdmin && vistaActual === 'residentes'" class="residentes-shell card">
          <div class="residentes-head">
            <div>
              <h3 class="admin-section-title">Residentes</h3>
              <p class="admin-section-sub">Solo el administrador puede registrar usuarios</p>
            </div>
            <button type="button" class="btn-accent" @click="abrirFormUsuario()">
              + Nuevo residente
            </button>
          </div>

          <div class="residentes-table-wrap">
            <table class="residentes-table">
              <thead>
                <tr>
                  <th>Residente</th>
                  <th>Correo</th>
                  <th>Rol</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="u in residentesFiltrados" :key="u.id">
                  <td>
                    <div class="residente-cell">
                      <span class="residente-avatar">{{ iniciales(u.nombre) }}</span>
                      <span class="residente-nombre">{{ u.nombre }}</span>
                    </div>
                  </td>
                  <td>{{ u.correo }}</td>
                  <td><span class="rol-pill">{{ u.rol }}</span></td>
                  <td>
                    <span
                      :class="[
                        'estado-pill',
                        estaVerificado(u) ? 'estado-pill--pagada' : 'estado-pill--pendiente',
                      ]"
                    >
                      {{ estaVerificado(u) ? 'Verificado' : 'Pendiente' }}
                    </span>
                  </td>
                  <td>
                    <div class="residente-actions">
                      <button
                        type="button"
                        class="icon-btn"
                        title="Editar"
                        @click="abrirFormUsuario(u)"
                      >
                        ✎
                      </button>
                      <button
                        v-if="!estaVerificado(u)"
                        type="button"
                        class="icon-btn"
                        title="Reenviar verificación"
                        @click="reenviarVerificacion(u)"
                      >
                        ✉
                      </button>
                      <button
                        type="button"
                        class="icon-btn icon-btn--danger"
                        title="Eliminar"
                        @click="eliminarUsuario(u)"
                      >
                        🗑
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-if="residentesFiltrados.length === 0" class="admin-empty">
              No hay residentes registrados.
            </p>
          </div>
        </div>

        <!-- Panel administrador: dashboard -->
        <div v-if="esAdmin && vistaActual === 'dashboard'" class="admin-shell">
          <div class="admin-layout">
            <div class="admin-main-col">
              <section class="admin-section card">
                <div class="admin-section-head">
                  <div>
                    <h3 class="admin-section-title">Multas</h3>
                    <p class="admin-section-sub">Registro y seguimiento de infracciones</p>
                  </div>
                  <button type="button" class="btn-accent" @click="abrirModal('multa')">
                    + Nueva multa
                  </button>
                </div>

                <div class="admin-list">
                  <TransitionGroup name="list-item">
                    <div
                      v-for="m in multasLista"
                      :key="m.id"
                      class="admin-list-row"
                    >
                      <div class="admin-list-main">
                        <span class="admin-list-badge">{{ m.residente_nombre }}</span>
                        <span class="admin-list-text">{{ m.descripcion }}</span>
                      </div>
                      <div class="admin-list-meta">
                        <span class="admin-list-monto">${{ Number(m.monto).toFixed(2) }}</span>
                        <span :class="['estado-pill', `estado-pill--${m.estado}`]">
                          {{ m.estado }}
                        </span>
                      </div>
                    </div>
                  </TransitionGroup>
                  <p v-if="multasLista.length === 0" class="admin-empty">
                    No hay multas. Pulsa «Nueva multa» para registrar una.
                  </p>
                </div>
              </section>

              <div class="admin-quick-actions">
                <button type="button" class="btn-accent-outline" @click="abrirModal('pago')">
                  + Pago atrasado
                </button>
                <button type="button" class="btn-accent-outline" @click="abrirModal('asamblea')">
                  + Nueva asamblea
                </button>
              </div>
            </div>

            <aside class="admin-historial card">
              <h3 class="admin-section-title">Historial</h3>
              <p class="admin-section-sub">Acciones realizadas en esta sesión</p>

              <div class="historial-list">
                <TransitionGroup name="historial">
                  <div
                    v-for="h in historial"
                    :key="h.id"
                    class="historial-item"
                  >
                    <span class="historial-icon">{{ tiposIconos[h.tipo] || '•' }}</span>
                    <div class="historial-body">
                      <div class="historial-titulo">{{ h.titulo }}</div>
                      <div class="historial-sub">{{ h.subtitulo }}</div>
                      <div class="historial-time">{{ haceCuanto(h.fecha) }}</div>
                    </div>
                  </div>
                </TransitionGroup>
                <p v-if="historial.length === 0" class="admin-empty">
                  Aún no hay acciones. Al crear multas, pagos o asambleas aparecerán aquí.
                </p>
              </div>
            </aside>
          </div>
        </div>

        <!-- Mensajes -->
        <div v-if="vistaActual === 'mensajes' || !esAdmin" class="card messages-shell">
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

  <!-- Modales administrador con transición -->
  <Transition name="modal-fade">
    <div
      v-if="modalActivo && esAdmin"
      class="admin-modal-overlay"
      @click.self="cerrarModal"
    >
      <Transition name="modal-slide" appear>
        <div
          v-if="modalActivo"
          class="admin-modal"
          role="dialog"
          aria-modal="true"
          @click.stop
        >
          <!-- Modal Multa -->
          <template v-if="modalActivo === 'multa'">
            <h3 class="admin-modal-title">Nueva multa</h3>
            <div class="admin-modal-field">
              <label>Departamento</label>
              <select v-model="adminUsuarioIdDestino">
                <option v-for="u in usuarios.filter(x => x.rol !== 'admin')" :key="u.id" :value="u.id">
                  {{ u.nombre }}
                </option>
              </select>
            </div>
            <div class="admin-modal-field">
              <label>Motivo</label>
              <input v-model="formMulta.descripcion" placeholder="Ej: Ruido excesivo" />
            </div>
            <div class="admin-modal-field">
              <label>Monto ($)</label>
              <input v-model="formMulta.monto" type="number" step="0.01" placeholder="0.00" />
            </div>
            <div class="admin-modal-field">
              <label>Estado</label>
              <select v-model="formMulta.estado">
                <option value="pendiente">Pendiente</option>
                <option value="pagada">Pagada</option>
                <option value="cancelada">Cancelada</option>
              </select>
            </div>
            <div class="admin-modal-field">
              <label>Fecha límite (opcional)</label>
              <input v-model="formMulta.fecha_vencimiento" type="date" />
            </div>
            <div class="admin-modal-actions">
              <button type="button" class="btn-ghost" @click="cerrarModal">Cancelar</button>
              <button
                type="button"
                class="btn-accent"
                :disabled="estaCargando('multa')"
                @click="crearMulta"
              >
                <Transition name="btn-swap" mode="out-in">
                  <span v-if="estaCargando('multa')" key="loading" class="btn-estado btn-estado--loading">
                    <span class="spinner spinner--light" aria-hidden="true" />
                    Cargando...
                  </span>
                  <span v-else key="idle" class="btn-estado">Crear multa</span>
                </Transition>
              </button>
            </div>
          </template>

          <!-- Modal Pago atrasado -->
          <template v-else-if="modalActivo === 'pago'">
            <h3 class="admin-modal-title">Pago atrasado</h3>
            <div class="admin-modal-field">
              <label>Residente</label>
              <select v-model="adminUsuarioIdDestino">
                <option v-for="u in usuarios.filter(x => x.rol !== 'admin')" :key="u.id" :value="u.id">
                  {{ u.nombre }}
                </option>
              </select>
            </div>
            <div class="admin-modal-field">
              <label>Concepto</label>
              <input v-model="formPago.concepto" placeholder="Ej: Cuota de mantenimiento" />
            </div>
            <div class="admin-modal-field">
              <label>Monto ($)</label>
              <input v-model="formPago.monto" type="number" step="0.01" />
            </div>
            <div class="admin-modal-field">
              <label>Días de atraso</label>
              <input v-model="formPago.dias_atraso" type="number" min="0" />
            </div>
            <div class="admin-modal-field">
              <label>Fecha de vencimiento</label>
              <input v-model="formPago.fecha_vencimiento" type="datetime-local" />
            </div>
            <div class="admin-modal-actions">
              <button type="button" class="btn-ghost" @click="cerrarModal">Cancelar</button>
              <button
                type="button"
                class="btn-accent"
                :disabled="estaCargando('pago')"
                @click="crearPagoAtrasado"
              >
                <Transition name="btn-swap" mode="out-in">
                  <span v-if="estaCargando('pago')" key="loading" class="btn-estado btn-estado--loading">
                    <span class="spinner spinner--light" aria-hidden="true" />
                    Cargando...
                  </span>
                  <span v-else key="idle" class="btn-estado">Registrar pago</span>
                </Transition>
              </button>
            </div>
          </template>

          <!-- Modal Asamblea -->
          <template v-else-if="modalActivo === 'asamblea'">
            <h3 class="admin-modal-title">Nueva asamblea</h3>
            <div class="admin-modal-field">
              <label>Título</label>
              <input v-model="formAsamblea.titulo" placeholder="Asamblea general" />
            </div>
            <div class="admin-modal-field">
              <label>Descripción</label>
              <input v-model="formAsamblea.descripcion" placeholder="Temas a tratar" />
            </div>
            <div class="admin-modal-field">
              <label>Fecha y hora</label>
              <input v-model="formAsamblea.fecha" type="datetime-local" />
            </div>
            <div class="admin-modal-field">
              <label>Lugar</label>
              <input v-model="formAsamblea.lugar" placeholder="Salón de eventos" />
            </div>
            <div class="admin-modal-field">
              <label>Agenda (opcional)</label>
              <input v-model="formAsamblea.agenda" placeholder="Puntos del orden del día" />
            </div>
            <div class="admin-modal-actions">
              <button type="button" class="btn-ghost" @click="cerrarModal">Cancelar</button>
              <button
                type="button"
                class="btn-accent"
                :disabled="estaCargando('asamblea')"
                @click="crearAsamblea"
              >
                <Transition name="btn-swap" mode="out-in">
                  <span v-if="estaCargando('asamblea')" key="loading" class="btn-estado btn-estado--loading">
                    <span class="spinner spinner--light" aria-hidden="true" />
                    Cargando...
                  </span>
                  <span v-else key="idle" class="btn-estado">Crear asamblea</span>
                </Transition>
              </button>
            </div>
          </template>

          <!-- Modal Usuario (CRUD admin) -->
          <template v-else-if="modalActivo === 'usuario'">
            <h3 class="admin-modal-title">
              {{ formUsuario.id ? 'Editar residente' : 'Nuevo residente' }}
            </h3>
            <p v-if="!formUsuario.id" class="modal-hint">
              Se enviará un correo de verificación al registrarse. Solo el admin puede crear usuarios.
            </p>
            <div class="admin-modal-field">
              <label>Nombre</label>
              <input v-model="formUsuario.nombre" placeholder="Nombre completo" />
            </div>
            <div class="admin-modal-field">
              <label>Correo</label>
              <input v-model="formUsuario.correo" type="email" placeholder="correo@ejemplo.com" />
            </div>
            <div class="admin-modal-field">
              <label>{{ formUsuario.id ? 'Nueva contraseña (opcional)' : 'Contraseña' }}</label>
              <input v-model="formUsuario.password" type="password" placeholder="••••••••" />
            </div>
            <div class="admin-modal-field">
              <label>Rol</label>
              <select v-model="formUsuario.rol">
                <option value="usuario">Residente</option>
                <option value="admin">Administrador</option>
              </select>
            </div>
            <div class="admin-modal-actions">
              <button type="button" class="btn-ghost" @click="cerrarModal">Cancelar</button>
              <button
                type="button"
                class="btn-accent"
                :disabled="estaCargando(formUsuario.id ? `usuario-edit-${formUsuario.id}` : 'usuario-create')"
                @click="guardarUsuario"
              >
                <Transition name="btn-swap" mode="out-in">
                  <span
                    v-if="estaCargando(formUsuario.id ? `usuario-edit-${formUsuario.id}` : 'usuario-create')"
                    key="loading"
                    class="btn-estado btn-estado--loading"
                  >
                    <span class="spinner spinner--light" aria-hidden="true" />
                    Cargando...
                  </span>
                  <span v-else key="idle" class="btn-estado">
                    {{ formUsuario.id ? 'Guardar cambios' : 'Registrar y enviar correo' }}
                  </span>
                </Transition>
              </button>
            </div>
          </template>
        </div>
      </Transition>
    </div>
  </Transition>

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
    linear-gradient(180deg, rgba(15, 23, 42, 0.62), rgba(15, 23, 42, 0.3)),
    url("https://inmobli.com/wp-content/uploads/2021/08/aerea-edificios-amenidades-2-ok-departamentos-diamante-queretaro-1.jpg") center/cover no-repeat;
  background-attachment: fixed;
  filter: saturate(0.9) brightness(0.78);
}

.auth-shell::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top left, rgba(255,255,255,0.12), transparent 22%),
    radial-gradient(circle at bottom right, rgba(255,255,255,0.08), transparent 18%);
  pointer-events: none;
}

.auth-card {
  position: relative;
  width: min(420px, 92vw);
  background: #ffffff;
  border-radius: 32px;
  padding: 36px 28px 32px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 34px 90px rgba(15, 23, 42, 0.16);
  backdrop-filter: blur(12px);
}

.auth-recovery {
  margin-top: 22px;
  padding: 26px;
  border-radius: 28px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
}

.auth-recovery-header {
  margin-bottom: 18px;
}

.auth-recovery-header h2 {
  margin: 0 0 6px;
  font-size: 1.15rem;
  font-weight: 800;
  color: #111827;
}

.auth-recovery-header p {
  margin: 0;
  color: #475569;
  font-size: 0.96rem;
  line-height: 1.6;
}

.auth-recovery .auth-field {
  margin-top: 16px;
}

.auth-recovery-note {
  margin: 16px 0 0;
  color: #6b7280;
  font-size: 0.92rem;
  line-height: 1.6;
}

.auth-logo {
  width: 52px;
  height: 52px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  margin: 0 auto 18px;
  width: 72px;
  height: 72px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: #111827;
  box-shadow: 0 24px 50px rgba(15, 23, 42, 0.22);
}

.auth-logo-icon {
  font-size: 1.85rem;
  color: #ffffff;
}

.auth-title {
  margin: 0;
  text-align: center;
  font-size: 34px;
  font-weight: 900;
  letter-spacing: -0.04em;
  color: #111827;
}

.auth-subtitle {
  margin: 8px 0 24px;
  text-align: center;
  color: #64748b;
  font-size: 15px;
  line-height: 1.7;
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
  padding: 16px 18px;
  border: 1px solid #e5e7eb;
  border-radius: 22px;
  background: #f7f9fc;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.auth-field input:focus {
  border-color: #2f80ed;
  box-shadow: 0 0 0 4px rgba(47, 128, 237, 0.12);
  transform: translateY(-1px);
}

.auth-field--code {
  margin-top: 20px;
  overflow: hidden;
}

.auth-field--code .auth-code-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 16px;
  padding: 0 8px;
}

.auth-code-digit {
  width: 100%;
  min-height: 72px;
  min-width: 0;
  border-radius: 22px;
  border: 2px solid #dae3ef;
  background: #ffffff;
  color: #000000;
  font-size: 3rem;
  font-weight: 900;
  text-align: center;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
  letter-spacing: 0;
  -webkit-font-smoothing: antialiased;
}

.auth-code-digit::placeholder {
  color: #cbd5e1;
}

.auth-code-digit:focus {
  border-color: #2f80ed;
  box-shadow: 0 0 0 5px rgba(47, 128, 237, 0.18);
  transform: translateY(-1px);
}

.auth-field--code label {
  margin-bottom: 12px;
}

.auth-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 16px 0 18px;
}

.auth-check {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  color: #475569;
  font-size: 13px;
}

.auth-check input {
  width: 14px;
  height: 14px;
}

.auth-link {
  color: #111827;
  font-size: 13px;
  text-decoration: none;
  opacity: 0.9;
  font-weight: 700;
}

.auth-link:hover {
  opacity: 1;
  text-decoration: underline;
}

.auth-btn {
  width: 100%;
  padding: 18px 20px;
  border: none;
  border-radius: 18px;
  background: #111827;
  color: #fff;
  font-weight: 800;
  font-size: 15px;
  cursor: pointer;
  box-shadow: 0 24px 40px rgba(17, 24, 39, 0.18);
  transition: transform 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.auth-btn:hover {
  background: #0f172a;
  transform: translateY(-2px);
  box-shadow: 0 24px 60px rgba(17, 24, 39, 0.22);
}

.auth-btn:disabled {
  opacity: 0.75;
  cursor: not-allowed;
  box-shadow: none;
}

.btn-ghost {
  width: 100%;
  padding: 14px 18px;
  border: 1px solid #d1d5db;
  border-radius: 18px;
  background: #ffffff;
  color: #475569;
  font-weight: 700;
  cursor: pointer;
  margin-top: 14px;
}

.btn-ghost:hover {
  background: #f8fafc;
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

/* Panel administrador */
.admin-shell {
  --accent: #0b0b0b;
  --accent-hover: #000;
  --accent-soft: #f5a623;
}

.admin-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 16px;
  align-items: start;
}

.admin-section {
  padding: 0;
  overflow: hidden;
}

.admin-section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-bottom: 1px solid #eef2f7;
  background: linear-gradient(180deg, #fafafa, #fff);
}

.admin-section-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 900;
  color: #0f172a;
}

.admin-section-sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: #64748b;
}

.btn-accent {
  padding: 10px 16px;
  border: none;
  border-radius: 10px;
  background: var(--accent);
  color: #fff;
  font-weight: 800;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  box-shadow: 0 8px 20px rgba(11, 11, 11, 0.18);
  transition: background 0.2s ease, transform 0.2s ease;
}

.btn-accent:hover:not(:disabled) {
  background: var(--accent-hover);
  transform: translateY(-1px);
}

.btn-accent:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-accent-outline {
  padding: 10px 16px;
  border: 1px solid #0f172a;
  border-radius: 10px;
  background: #fff;
  color: #0f172a;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-accent-outline:hover {
  background: #0f172a;
  color: #fff;
}

.btn-ghost {
  padding: 10px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  color: #64748b;
  font-weight: 700;
  cursor: pointer;
}

.admin-list {
  padding: 8px 0;
}

.admin-list-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 20px;
  border-bottom: 1px solid #f1f5f9;
  transition: background 0.2s ease;
}

.admin-list-row:hover {
  background: #fafafa;
}

.admin-list-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.admin-list-badge {
  font-size: 12px;
  font-weight: 800;
  color: #0f172a;
}

.admin-list-text {
  font-size: 13px;
  color: #64748b;
}

.admin-list-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  flex-shrink: 0;
}

.admin-list-monto {
  font-weight: 900;
  color: #0f172a;
  font-size: 14px;
}

.estado-pill {
  font-size: 11px;
  font-weight: 800;
  text-transform: capitalize;
  padding: 4px 10px;
  border-radius: 999px;
}

.estado-pill--pendiente {
  background: #fef3c7;
  color: #92400e;
}

.estado-pill--pagada {
  background: #d1fae5;
  color: #065f46;
}

.estado-pill--cancelada {
  background: #f1f5f9;
  color: #475569;
}

.admin-empty {
  padding: 24px 20px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  margin: 0;
}

.admin-quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.admin-historial {
  padding: 18px 16px;
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
}

.historial-list {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.historial-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
}

.historial-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.historial-titulo {
  font-size: 13px;
  font-weight: 800;
  color: #0f172a;
}

.historial-sub {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
  line-height: 1.4;
}

.historial-time {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 6px;
}

/* Transición lista multas / historial */
.list-item-enter-active,
.list-item-leave-active {
  transition: all 0.35s ease;
}

.list-item-enter-from {
  opacity: 0;
  transform: translateX(-12px);
}

.list-item-leave-to {
  opacity: 0;
  transform: translateX(12px);
}

.historial-enter-active,
.historial-leave-active {
  transition: all 0.35s ease;
}

.historial-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.historial-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.historial-move {
  transition: transform 0.35s ease;
}

/* Modales administrador */
.admin-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 5000;
  background: rgba(15, 23, 42, 0.45);
  display: grid;
  place-items: center;
  padding: 20px;
}

.admin-modal {
  width: min(440px, 100%);
  background: #fff;
  border-radius: 14px;
  padding: 24px 22px 20px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.22);
}

.admin-modal-title {
  margin: 0 0 18px;
  font-size: 1.15rem;
  font-weight: 900;
  color: #0f172a;
}

.admin-modal-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}

.admin-modal-field label {
  font-size: 12px;
  font-weight: 700;
  color: #475569;
}

.admin-modal-field input,
.admin-modal-field select {
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 14px;
  outline: none;
}

.admin-modal-field input:focus,
.admin-modal-field select:focus {
  border-color: #0f172a;
  box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.1);
}

.admin-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
  padding-top: 8px;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.28s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-slide-enter-active,
.modal-slide-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.modal-slide-enter-from {
  opacity: 0;
  transform: translateY(24px) scale(0.96);
}

.modal-slide-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.98);
}

.modal-hint {
  margin: -8px 0 14px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.45;
}

.auth-verify-banner {
  margin-top: 16px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  font-size: 13px;
  color: #92400e;
  text-align: left;
}

/* CRUD Residentes */
.residentes-shell {
  padding: 0;
  overflow: hidden;
}

.residentes-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-bottom: 1px solid #eef2f7;
}

.residentes-table-wrap {
  overflow-x: auto;
}

.residentes-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.residentes-table th {
  text-align: left;
  padding: 12px 16px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #94a3b8;
  border-bottom: 1px solid #eef2f7;
}

.residentes-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.residente-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.residente-avatar {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  background: #f1f5f9;
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 12px;
  color: #475569;
}

.residente-nombre {
  font-weight: 700;
  color: #0f172a;
}

.rol-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  text-transform: capitalize;
}

.residente-actions {
  display: flex;
  gap: 6px;
}

.icon-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  display: grid;
  place-items: center;
}

.icon-btn:hover {
  background: #f8fafc;
}

.icon-btn--danger:hover {
  background: #fef2f2;
  border-color: #fecaca;
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

  .admin-layout {
    grid-template-columns: 1fr;
  }

  .admin-historial {
    position: static;
    max-height: none;
  }

  .admin-section-head {
    flex-direction: column;
    align-items: stretch;
  }

  .message {
    max-width: 85vw;
  }

  .auth-card {
    width: min(100%, 100vw);
    margin: 0 auto;
    padding: 28px 22px 30px;
    border-radius: 36px;
    border: 1px solid rgba(255, 255, 255, 0.55);
    background: rgba(255, 255, 255, 0.94);
  }

  .auth-recovery {
    padding: 22px;
  }

  .auth-code-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 8px;
  }

  .auth-code-digit {
    min-height: 52px;
  }
}

</style>