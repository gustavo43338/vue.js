<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import echo from './echo'

const mensaje = ref('')
const mensajes = ref([])

const enviar = async () => {

  await axios.post(
    'http://127.0.0.1:8000/api/mensaje',
    {
      mensaje: mensaje.value
    }
  )

  mensaje.value = ''
}

onMounted(() => {

  echo.channel('chat-channel')
    .listen('.nuevo-mensaje', (e) => {

      mensajes.value.push(e.mensaje)

      console.log(e)
    })
})
</script>

<template>

<div style="padding:20px">

  <h1>Chat WebSocket</h1>

  <input v-model="mensaje" />

  <button @click="enviar">
    Enviar
  </button>

  <ul>
    <li
      v-for="(m, i) in mensajes"
      :key="i"
    >
      {{ m }}
    </li>
  </ul>

</div>

</template>