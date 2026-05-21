# VertebraAI — Frontend

[![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![Babel](https://img.shields.io/badge/Babel-Standalone-F9DC3E?logo=babel&logoColor=black)](https://babeljs.io/)
[![AWS S3](https://img.shields.io/badge/AWS-S3%20Static%20Hosting-FF9900?logo=amazonaws&logoColor=white)](https://aws.amazon.com/s3/)
[![License](https://img.shields.io/badge/License-Académica%20Uniandes-004B87)](https://uniandes.edu.co/)

> **Aviso clínico:** Esta herramienta es un apoyo diagnóstico exclusivamente. Toda decisión clínica debe ser revisada por un radiólogo o especialista cualificado.

SPA (Single Page Application) en React 18 + Babel standalone — sin paso de build — que consume el servicio `services/` para análisis automático de radiografías de columna vertebral. Desarrollada como parte del proyecto de grado de la **Maestría en Inteligencia Artificial (MaIA)** — Universidad de los Andes, 2026.

---

## Tabla de contenidos

- [Descripción del frontend](#descripción-del-frontend)
  - [Funcionalidades](#funcionalidades)
  - [Estructura](#estructura)
- [Dependencias](#dependencias)
- [Entorno de ejecución](#entorno-de-ejecución)
- [Pasos de despliegue](#pasos-de-despliegue)
  - [Local](#local)
  - [Producción (AWS S3 + CloudFront)](#producción-aws-s3--cloudfront)
- [Configuración](#configuración)
  - [URL del backend](#url-del-backend)
  - [Apariencia](#apariencia)
- [Credenciales de ejemplo](#credenciales-de-ejemplo)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Contribución](#contribución)
- [Licencia](#licencia)

---

## Descripción del frontend

Interfaz web estática que no requiere servidor de aplicaciones ni proceso de compilación. Los archivos se sirven directamente desde cualquier servidor HTTP estático (S3, `serve`, Python, nginx). React y Babel se cargan desde CDN con integridad SRI verificada.

### Funcionalidades

- **Login con AWS Cognito** — autenticación vía `POST /api/vertebraai/auth/login`, token JWT guardado en `localStorage`
- **Recuperación de contraseña** — flujo OTP de dos pasos (`forgot-password` → `confirm-password`)
- **Subida de radiografías** — drag & drop o selector de archivo (PNG / JPEG, mínimo 32×32 px)
- **Selección de modelo** — tarjetas con métricas de cada modelo antes de analizar
- **Visualización con slider** — comparador deslizable original / segmentado con zoom y pan
- **Bounding boxes interactivos** — click en vértebras del panel lateral para superponer cajas sobre la máscara
- **Comparación multi-modelo** — hasta 3 paneles simultáneos con el mismo archivo
- **Exportar resultados** — descarga de original, máscara, overlay y reporte JSON con token auth

### Estructura

```
frontend/
├── index.html          Entry point: carga CDN, config.js y los scripts JSX
├── app.jsx             App principal: LoginView, UploadZone, ResultView, CompareView
├── tweaks-panel.jsx    Panel de ajustes en runtime (tema oscuro/claro)
├── styles.css          Estilos Material 3 (dark mode por defecto)
├── config.js           URL del backend — generado por Terraform en producción
└── package.json        Script npm start (serve local en :5500)
```

---

## Dependencias

Sin dependencias de runtime en `node_modules` — todo se carga desde CDN con verificación de integridad (SRI).

| Librería | Versión | Carga |
|----------|---------|-------|
| React | 18.3.1 | CDN (unpkg) |
| ReactDOM | 18.3.1 | CDN (unpkg) |
| Babel Standalone | 7.29.0 | CDN (unpkg) |

**Dependencia de desarrollo** (solo para el servidor local):

| Paquete | Versión | Uso |
|---------|---------|-----|
| `serve` | ^14.2.4 | Servidor HTTP estático para desarrollo local |

---

## Entorno de ejecución

| Componente | Requisito |
|------------|-----------|
| Node.js / npx | 18+ (solo para `npm start` local) |
| Navegador | Chrome 90+, Firefox 88+, Safari 14+ |
| Backend | Servicio `services/` corriendo y accesible |

No se requiere Python, Docker ni ningún compilador. Los archivos JSX son transpilados en el navegador por Babel Standalone.

---

## Pasos de despliegue

### Local

```bash
# 1. Asegurarse de que el backend esté corriendo (en otro terminal)
cd services
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# o con Docker:
# docker run -p 8000:8000 -e AUTH_ENABLED=false vertebraai

# 2. Servir el frontend
cd frontend

# Opción A — npm (recomendado)
npm install        # solo la primera vez, instala 'serve'
npm start          # corre: serve . -l 5500

# Opción B — npx sin instalar
npx serve . -l 5500

# Opción C — Python (sin Node)
python3 -m http.server 5500

# 3. Abrir en el navegador
open http://localhost:5500/
```

> Abrir `index.html` directamente como `file://` **no funciona**: el navegador bloquea las peticiones `fetch` a localhost por política de origen cruzado (CORS).

### Producción (AWS S3 + CloudFront)

El despliegue en producción se gestiona desde Terraform en la raíz del monorepo. Terraform:

1. Genera `config.js` con `window.BACKEND_URL = ""` (ruta relativa vía CloudFront)
2. Sincroniza `frontend/` al bucket S3
3. Invalida la caché de CloudFront

```bash
# Desde terraform/
terraform apply -target=null_resource.deploy_frontend
```

Para el despliegue completo ver [`../terraform/`](../terraform/) y la sección **AWS (Terraform)** del [README raíz](../README.md).

---

## Configuración

El frontend no usa variables de entorno del sistema. Su configuración se controla mediante dos mecanismos:

### URL del backend

El archivo `config.js` define la variable global `window.BACKEND_URL`, que determina a dónde apuntan todas las peticiones del frontend.

| Contexto | Valor de `window.BACKEND_URL` | Resultado |
|----------|-------------------------------|-----------|
| Producción (CloudFront) | `""` *(string vacío)* | Rutas relativas — `/api/*` se enrutan al backend vía CloudFront |
| Desarrollo local | `"http://localhost:8000"` | Peticiones directas al backend local |
| Backend en otro host | `"http://mi-servidor:8080"` | Peticiones al host indicado |

**En producción** `config.js` es generado automáticamente por Terraform — no editar a mano ni commitear cambios en este archivo (está en `.gitignore`).

**En desarrollo local** editar `config.js` manualmente si el backend corre en un puerto distinto al `8000`:

```js
// config.js — solo para desarrollo local
window.BACKEND_URL = "http://localhost:8000";
```

También se puede sobreescribir desde la consola del navegador sin tocar archivos:

```js
// Solo aplica hasta recargar la página
window.BACKEND_URL = "http://192.168.1.100:8000";
```

### Apariencia

El panel de ajustes (botón ⚙ en la esquina del frontend) permite cambiar el **tema** en runtime sin recargar la página. La preferencia se persiste en `localStorage`.

| Parámetro | Valores | Valor por defecto |
|-----------|---------|-------------------|
| `theme` | `dark` · `light` | `dark` |

El valor por defecto se define en la constante `TWEAK_DEFAULTS` dentro de `app.jsx` (línea marcada con `/*EDITMODE-BEGIN*/`):

```js
const TWEAK_DEFAULS = /*EDITMODE-BEGIN*/{
  "theme": "dark"
}/*EDITMODE-END*/;
```

---

## Credenciales de ejemplo

El frontend delega la autenticación al backend (AWS Cognito). Para iniciar sesión usar el usuario de prueba del proyecto:

| Campo | Valor |
|-------|-------|
| Usuario | `maia_groupo5` |
| Contraseña | *(solicitar por canal seguro)* |

> Para desarrollo local sin Cognito, arrancar el backend con `AUTH_ENABLED=false` — el frontend omite el login y entra directamente a la pantalla de carga.

---

## Ejemplos de uso

1. Abrir `http://localhost:5500/` en el navegador
2. Iniciar sesión con las credenciales de ejemplo
3. Arrastrar una radiografía AP en formato PNG o JPEG al área de carga
4. Seleccionar el modelo deseado en el panel derecho (por defecto: *MedSAM + VertebraPrompt*)
5. Esperar el análisis (~30 s en CPU)
6. Explorar los resultados:
   - Mover el **slider** para comparar original vs segmentado
   - Hacer **click en una vértebra** del panel lateral para ver su bounding box
   - Usar **Acciones → Exportar** para descargar la máscara o el reporte JSON
   - Usar **Comparar** para ejecutar el mismo archivo con otro modelo en paralelo

---

## Contribución

1. Crear rama: `git checkout -b feature/nombre-feature`
2. Editar `app.jsx` o `styles.css` según el cambio
3. Verificar en el navegador en `http://localhost:5500/` (no hay tests automatizados en el frontend)
4. Abrir Pull Request con capturas de pantalla del cambio visual

---

## Licencia

Proyecto académico — Universidad de los Andes, MaIA 2026. Uso restringido a fines educativos e investigativos.
