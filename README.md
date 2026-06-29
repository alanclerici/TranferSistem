# Tranfersistem

Tranfersistem es una aplicacion web local para compartir archivos en una red LAN. Se ejecuta en una PC con Ubuntu y permite que otras PCs de la misma red, por ejemplo Windows, entren desde el navegador para ver, descargar, subir y borrar archivos dentro de una carpeta compartida.

La interfaz tiene estetica terminal/CRT verde y no usa frontend pesado: solo FastAPI, Jinja2, HTML y CSS local.

Importante: no tiene login ni autenticacion. Usar solo en redes locales confiables. No exponer directamente a Internet.

## Caracteristicas

- Pagina principal web accesible desde la LAN.
- Directorio raiz configurable.
- Lista archivos y carpetas existentes.
- Permite navegar carpetas existentes, pero no crear carpetas desde la web.
- Permite subir uno o varios archivos a la carpeta actual.
- Evita sobrescritura accidental: si `archivo.txt` ya existe, guarda `archivo_1.txt`, `archivo_2.txt`, etc.
- Permite descargar archivos.
- Permite borrar archivos. El borrado esta habilitado por defecto.
- No permite borrar carpetas desde la web.
- Soporta nombres con espacios y caracteres habituales en espanol.
- Bloquea path traversal con `Path.resolve()` y validacion contra el directorio raiz permitido.
- Limite configurable de tamano maximo por archivo subido.

## Requisitos

- Ubuntu o una distribucion Linux similar.
- Python 3.11 o superior.
- Acceso a la red local.
- Opcional: `ufw` si se usa firewall en Ubuntu.
- Opcional: `systemd` para autoinicio.

En Ubuntu, si falta el soporte de entornos virtuales:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

## Instalacion desde cero

Clonar el repositorio:

```bash
git clone <URL_DEL_REPO>
cd local-crt-filedrop
```

Crear y activar el entorno virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Crear la carpeta compartida. Puede ser cualquier ruta, pero este ejemplo usa:

```bash
mkdir -p "$HOME/CompartidoWeb"
```

Crear el archivo de configuracion local:

```bash
cp .env.example .env
```

Editar `.env` y ajustar la ruta compartida si hace falta:

```bash
LOCAL_CRT_SHARED_ROOT=/home/tu_usuario/CompartidoWeb
LOCAL_CRT_MAX_UPLOAD_SIZE_MB=512
LOCAL_CRT_DELETE_ENABLED=true
LOCAL_CRT_HOST=0.0.0.0
LOCAL_CRT_PORT=8000
```

## Ejecutar manualmente

El proyecto incluye un wrapper ejecutable en:

```text
scripts/tranfersistem
```

El formato recomendado es un shell script sin extension, con shebang. En Linux se usa como un comando normal y no hace falta escribir `.sh`.

Para instalarlo en un directorio del `PATH`, por ejemplo `~/.local/bin`:

```bash
install -D -m 755 scripts/tranfersistem "$HOME/.local/bin/tranfersistem"
```

Despues se puede ejecutar desde cualquier directorio:

```bash
tranfersistem
```

El wrapper usa por defecto la carpeta `shared` dentro del proyecto y escucha en `0.0.0.0:8000`. Se puede cambiar con variables de entorno:

```bash
LOCAL_CRT_SHARED_ROOT="$HOME/CompartidoWeb" tranfersistem
LOCAL_CRT_PORT=9000 tranfersistem
```

Tambien se puede ejecutar directamente con `uvicorn` desde la carpeta del proyecto:

```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

En la PC donde corre el servidor:

```text
http://localhost:8000
```

Desde otra PC de la LAN se usa la IP local de Ubuntu.

## Encontrar la IP local de Ubuntu

Opcion simple:

```bash
hostname -I
```

O ver todas las interfaces:

```bash
ip a
```

Si la IP de Ubuntu es `192.168.1.50`, desde otra PC abrir:

```text
http://192.168.1.50:8000
```

## Firewall

Si `ufw` esta activo, abrir el puerto:

```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

## Configuracion

La app lee variables de entorno con prefijo `LOCAL_CRT_`. Si existe un archivo `.env` en la raiz del proyecto, tambien lo carga.

Variables disponibles:

```bash
LOCAL_CRT_SHARED_ROOT=/home/tu_usuario/CompartidoWeb
LOCAL_CRT_MAX_UPLOAD_SIZE_MB=512
LOCAL_CRT_DELETE_ENABLED=true
LOCAL_CRT_HOST=0.0.0.0
LOCAL_CRT_PORT=8000
```

Detalles:

- `LOCAL_CRT_SHARED_ROOT`: carpeta raiz permitida. La app no puede navegar fuera de esta ruta.
- `LOCAL_CRT_MAX_UPLOAD_SIZE_MB`: tamano maximo por archivo subido.
- `LOCAL_CRT_DELETE_ENABLED`: `true` permite borrar archivos; `false` oculta/deshabilita el borrado.
- `LOCAL_CRT_HOST`: host por defecto si se ejecuta con `python -m app.main`.
- `LOCAL_CRT_PORT`: puerto por defecto si se ejecuta con `python -m app.main`.

## Autoinicio con systemd

Hay un servicio de ejemplo en:

```text
systemd/local-crt-filedrop.service
```

Antes de instalarlo, editar estas lineas para que coincidan con el usuario y ruta reales:

```ini
User=tu_usuario
WorkingDirectory=/ruta/al/local-crt-filedrop
EnvironmentFile=-/ruta/al/local-crt-filedrop/.env
ExecStart=/ruta/al/local-crt-filedrop/venv/bin/python -m app.main
```

Instalar el servicio:

```bash
sudo cp systemd/local-crt-filedrop.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now local-crt-filedrop
```

Ver estado:

```bash
systemctl status local-crt-filedrop
```

Ver logs en vivo:

```bash
journalctl -u local-crt-filedrop -f
```

Reiniciar despues de cambiar `.env` o actualizar el codigo:

```bash
sudo systemctl restart local-crt-filedrop
```

## Seguridad

Tranfersistem esta pensado para una red local confiable.

Sin autenticacion, cualquier equipo que pueda abrir `http://IP:PUERTO` puede:

- Ver archivos dentro del directorio compartido.
- Descargar archivos.
- Subir archivos.
- Borrar archivos si `LOCAL_CRT_DELETE_ENABLED=true`.

Medidas implementadas:

- Todas las rutas se resuelven con `Path.resolve()`.
- La ruta final siempre se valida contra el directorio raiz configurado.
- Se rechazan rutas absolutas recibidas desde la web.
- Se bloquean rutas como `../` y `../../etc/passwd`.
- No se ejecutan comandos del sistema con datos ingresados por usuarios.
- El tamano maximo de subida es configurable.
- El borrado se limita a archivos; no se borran carpetas desde la web.

No publicar esta aplicacion en Internet sin agregar autenticacion, HTTPS y controles de acceso.

## Desarrollo

Compilar/verificar sintaxis:

```bash
python3 -m compileall app
```

Ejecutar con recarga automatica:

```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
