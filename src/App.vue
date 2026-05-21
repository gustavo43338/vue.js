<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import echo from './echo'

const usuarios = [
  {
    email: 'juan@gmail.com',
    password: '123'
  },
  {
    email: 'maria@gmail.com',
    password: '123'
  }
]

const email = ref('')
const password = ref('')

const usuarioActual = ref(
  localStorage.getItem('usuario') || ''
)

const mensaje = ref('')

const mensajes = ref([])

const formatearHora = (fecha) => {
  if (!fecha) return ''
  
  const date = new Date(fecha)
  const horas = String(date.getHours()).padStart(2, '0')
  const minutos = String(date.getMinutes()).padStart(2, '0')
  
  return `${horas}:${minutos}`
}

const extraerNombre = (email) => {
  return email.split('@')[0]
}

const login = () => {

  const existe = usuarios.find(u =>
    u.email === email.value &&
    u.password === password.value
  )

  if (!existe) {
    alert('Usuario incorrecto')
    return
  }

  localStorage.setItem('usuario', existe.email)

  usuarioActual.value = existe.email
  
  cargarMensajes()
}

const logout = () => {

  localStorage.removeItem('usuario')

  usuarioActual.value = ''
}

const enviar = async () => {

  if (!mensaje.value) return

  await axios.post(
    'http://127.0.0.1:8000/api/mensaje',
    {
      usuario: usuarioActual.value,
      mensaje: mensaje.value
    }
  )

  mensaje.value = ''
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

onMounted(() => {

  if (usuarioActual.value) {
    cargarMensajes()
  }

  echo.channel('chat-channel')
    .listen('.nuevo-mensaje', (e) => {

      mensajes.value.push({
        usuario: e.usuario,
        mensaje: e.mensaje,
        created_at: e.created_at || new Date().toISOString()
      })

      console.log(e)
    })
})
</script>

<template>

<div class="container">

  <!-- LOGIN -->

  <div v-if="!usuarioActual" class="login">

    <h1>Chat Condominio</h1>

    <input
      v-model="email"
      placeholder="Correo"
      type="email"
    />

    <input
      v-model="password"
      type="password"
      placeholder="Contraseña"
    />

    <button @click="login">
      Entrar
    </button>

    <div class="users">
      Demo: juan@gmail.com / maria@gmail.com (password: 123)
    </div>

  </div>

  <!-- CHAT -->

  <div v-else class="chat-container">

    <div class="header">

      <div class="header-title">
        <h2>Chat Condominio</h2>
        <span class="users-count">{{ extraerNombre(usuarioActual) }}</span>
      </div>

      <button class="logout-btn" @click="logout">
        ✕
      </button>

    </div>

    <div class="chat" ref="chatContainer">

      <div
        v-for="(m, i) in mensajes"
        :key="i"
        :class="[
          'message-wrapper',
          m.usuario === usuarioActual
            ? 'mine'
            : 'other'
        ]"
      >

        <div class="message">

          <div v-if="m.usuario !== usuarioActual" class="sender-name">
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

      <button @click="enviar" class="send-btn">
        ⬆
      </button>

    </div>

  </div>

</div>

</template>

<style>

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', sans-serif;
  background: linear-gradient(135deg, #f5f5f5 0%, #fafafa 100%);
  color: #1a1a1a;
}

.container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login,
.chat-container {
  width: 100%;
  max-width: 960px;
  background: #ffffff;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
}

.login {
  padding: 48px 40px;
  text-align: center;
}

.login h1 {
  margin: 0 0 32px;
  font-size: 2.2rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #111111;
}

.login input {
  width: 100%;
  max-width: 360px;
  margin: 10px auto;
  display: block;
  padding: 14px 18px;
  border: 1px solid #ddd;
  border-radius: 12px;
  background: #f9f9f9;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.login input:focus {
  outline: none;
  border-color: #1a1a1a;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(26, 26, 26, 0.08);
}

.login button {
  width: 100%;
  max-width: 360px;
  margin-top: 16px;
  display: block;
  padding: 14px 24px;
  background: #1a1a1a;
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.login button:hover {
  background: #000000;
  transform: translateY(-1px);
}

.users {
  margin-top: 24px;
  font-size: 0.9rem;
  color: #666;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 40px);
  max-height: 80vh;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: #1a1a1a;
  color: white;
}

.header-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-title h2 {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.users-count {
  font-size: 0.85rem;
  opacity: 0.8;
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

.chat {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
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
  background: #1a1a1a;
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
  padding: 16px 24px 20px;
  background: #ffffff;
  border-top: 1px solid #eee;
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
  background: #1a1a1a;
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

@media (max-width: 768px) {
  .container {
    padding: 12px;
  }

  .login {
    padding: 36px 24px;
  }

  .login h1 {
    font-size: 1.8rem;
  }

  .chat-container {
    max-height: 100vh;
    height: 100vh;
    border-radius: 16px;
  }

  .message {
    max-width: 85vw;
  }
}

</style>