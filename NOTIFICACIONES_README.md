# 🔔 Sistema de Notificaciones Asincrónicas

Sistema completo de notificaciones en tiempo real para un condominio usando Laravel + Vue 3 + WebSocket (Reverb).

## 📋 Requisitos Previos

- PHP 8.2+
- PostgreSQL 12+
- Node.js 20+
- Composer
- Git

## 🚀 Instalación Rápida

### 1️⃣ Backend (Laravel)

```bash
cd c:\Users\gusta\proyectolaravel

# Instalar dependencias PHP
composer install

# Crear archivo .env (si no existe)
cp .env.example .env

# Generar clave de aplicación
php artisan key:generate

# Ejecutar migraciones
php artisan migrate

# Cargar datos de prueba
php artisan db:seed
```

### 2️⃣ Frontend (Vue)

```bash
cd c:\Users\gusta\proyectovuejs

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev
```

---

## ⚙️ Ejecutar Servidores

Necesitas **3 terminales** abiertas simultáneamente:

### **Terminal 1: Laravel API**
```bash
cd c:\Users\gusta\proyectolaravel
php artisan serve
# Escucha en: http://127.0.0.1:8000
```

### **Terminal 2: WebSocket (Reverb)**
```bash
cd c:\Users\gusta\proyectolaravel
php artisan reverb:start
# Escucha en: ws://127.0.0.1:8080
```

### **Terminal 3: Frontend Dev Server**
```bash
cd c:\Users\gusta\proyectovuejs
npm run dev
# Escucha en: http://localhost:5173
```

---

## 🔑 Credenciales de Prueba

Después de ejecutar `php artisan db:seed`, puedes usar:

| Email | Contraseña | Rol |
|-------|-----------|-----|
| juan@gmail.com | 123 | usuario |
| maria@gmail.com | 123 | usuario |
| admin@gmail.com | 123 | admin |

---

## 🎯 Características Implementadas

✅ **Botón de Notificaciones** con contador de no leídas
✅ **Panel Desplegable** con lista de notificaciones
✅ **Modal de Detalles** con información completa
✅ **WebSocket en Tiempo Real** via Laravel Reverb
✅ **4 Tipos de Notificaciones**: Mensajes, Multas, Asambleas, Pagos Atrasados
✅ **Login Funcional** con usuarios y administrador
✅ **Marca como Leída** automática y manual
✅ **Responsive Design** para móvil y desktop

---

## 📡 API Endpoints

### Notificaciones
```
GET    /api/notificaciones?usuario_id=1           # Listar todas
GET    /api/notificaciones/no-leidas?usuario_id=1 # No leídas
GET    /api/notificaciones/{id}                    # Detalle
PUT    /api/notificaciones/{id}/leida              # Marcar leída
PUT    /api/notificaciones/marcar-todas-leidas    # Marcar todas
```

### Multas
```
POST   /api/multas
GET    /api/multas/{usuarioId}
GET    /api/multas/{id}
PUT    /api/multas/{id}
```

### Asambleas
```
POST   /api/asambleas
GET    /api/asambleas
GET    /api/asambleas/{id}
PUT    /api/asambleas/{id}
```

### Pagos Atrasados
```
POST   /api/pagos-atrasados
GET    /api/pagos-atrasados/{usuarioId}
GET    /api/pagos-atrasados/{id}
```

---

## 🔌 Canales WebSocket

### Privados (usuario específico)
```javascript
echo.private(`usuario.${usuarioId}`)
  .listen('.notificacion-nueva', (data) => {...})
  .listen('.multa-nueva', (data) => {...})
  .listen('.pago-atrasado-nuevo', (data) => {...})
```

### Públicos
```javascript
echo.channel('asambleas')
  .listen('.asamblea-nueva', (data) => {...})

echo.channel('chat-channel')
  .listen('.nuevo-mensaje', (data) => {...})
```

---

## 📊 Estructura de Base de Datos

### Tabla: notificaciones
- id, usuario_id, tipo (enum), referencia_id, titulo, descripcion, leida, fecha_lectura, timestamps

### Tabla: multas
- id, usuario_id, descripcion, monto, estado, detalles, fecha_vencimiento, timestamps

### Tabla: asambleas
- id, titulo, descripcion, fecha, lugar, agenda, estado, timestamps

### Tabla: pagos_atrasados
- id, usuario_id, concepto, monto, fecha_vencimiento, dias_atraso, detalles, timestamps

---

## 🧪 Probar Creación de Notificaciones

### Usar Postman o cURL

**Crear una Multa:**
```bash
curl -X POST http://127.0.0.1:8000/api/multas \
  -H "Content-Type: application/json" \
  -d '{
    "usuario_id": 1,
    "descripcion": "Ruido nocturno",
    "monto": 50,
    "estado": "pendiente",
    "fecha_vencimiento": "2026-06-01"
  }'
```

**Crear una Asamblea (notifica a todos):**
```bash
curl -X POST http://127.0.0.1:8000/api/asambleas \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Asamblea Extraordinaria",
    "descripcion": "Temas importantes",
    "fecha": "2026-06-15 18:00:00",
    "lugar": "Salón de eventos",
    "agenda": "Reforma reglamento"
  }'
```

---

## 🐛 Troubleshooting

### Error: CORS
Edita `config/cors.php` en Laravel:
```php
'allowed_origins' => ['http://localhost:5173']
```

### Error: Base de datos no conecta
Verifica credenciales en `.env`:
- DB_CONNECTION=pgsql
- DB_HOST=127.0.0.1
- DB_PORT=5432
- DB_DATABASE=laravel
- DB_USERNAME=postgres

### Error: WebSocket no conecta
- Verifica que Reverb esté corriendo: `php artisan reverb:start`
- Verifica puerto 8080 no esté bloqueado

### Error: Notificaciones no llegan
- Abre DevTools (F12) → Console
- Verifica que no haya errores de conexión
- Recarga la página después de iniciar Reverb

---

## 📚 Documentación Completa

Ver `NOTIFICACIONES_GUIA.md` en la carpeta del proyecto Laravel para documentación detallada.

---

## 🤝 Soporte

Para más información sobre:
- Laravel: https://laravel.com/docs
- Reverb: https://reverb.laravel.com/docs
- Vue 3: https://vuejs.org/
- Echo: https://laravel.com/docs/broadcasting

---

**¡Sistema listo para usar! 🎉**
