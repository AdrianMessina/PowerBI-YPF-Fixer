# Power BI Fixer - Cómo Instalar

## Qué Necesitas Antes de Empezar

1. **Python instalado en tu computadora**
   - Si no lo tienes, descargalo de: https://www.python.org/downloads/
   - Cuando lo instales, marcá la casilla que dice "Add Python to PATH"

2. **Internet** (solo la primera vez que lo uses)

---

## Cómo Instalarlo (SUPER FÁCIL)

### Paso 1: Descomprimir el ZIP
- Hacé clic derecho en el archivo ZIP → "Extraer todo"
- Elegí dónde querés guardarlo (por ejemplo en tu escritorio o en Documentos)

### Paso 2: Ejecutar la aplicación
- Buscá el archivo que se llama: **Power BI Fixer.bat**
- Hacé **doble clic** en ese archivo

### Paso 3: Esperar
- La primera vez va a tardar un ratito (2-3 minutos) porque descarga las librerías que necesita
- Vas a ver una ventana negra con texto. NO LA CIERRES, dejala abierta
- Cuando termine, se va a abrir automáticamente en tu navegador

**¡Listo! Ya está funcionando**

---

## Qué Librerías Instala Automáticamente

El programa necesita estas 4 librerías para funcionar:

1. **PyYAML** - Para leer configuraciones
2. **Streamlit** - Para la interfaz visual
3. **Pandas** - Para trabajar con datos
4. **Plotly** - Para los gráficos

Todo esto se descarga e instala automáticamente cuando hacés doble clic en el .bat

**Tamaño total:** 150-200 MB aproximadamente (se descarga solo la primera vez)

---

## Si Estás en la Red de YPF

A veces la red corporativa no deja descargar cosas. Si te sale un error al instalar:

1. Abrí el archivo **Power BI Fixer.bat** con el Bloc de Notas (clic derecho → Editar)
2. Buscá la línea que dice: `pip install -r requirements.txt`
3. Cambiala por: `pip install --proxy http://proxy-azure -r requirements.txt`
4. Guardá el archivo y volvé a ejecutarlo

---

## Problemas Comunes y Cómo Solucionarlos

**Me dice "Python no se reconoce..."**
- Tenés que instalar Python. Bajalo de python.org y asegurate de tildar "Add Python to PATH"

**Se quedó trabado instalando las librerías**
- Probá cerrar todo y ejecutar el .bat de nuevo
- Si estás en YPF, probá el tema del proxy (ver arriba)

**No se abre el navegador**
- Abrí Chrome, Edge o Firefox y andá a esta dirección: http://localhost:8501

**Ya lo usé antes y ahora no funciona**
- Probá ejecutar el .bat de nuevo. Va a arrancar más rápido porque ya tiene todo instalado

---

## Cómo Usar la Aplicación

Cuando se abra en el navegador:

1. A la izquierda, elegí si vas a analizar un PBIP (proyecto) o PBIX (archivo)
2. Cargá tu archivo de Power BI
3. Dale al botón "Analizar"
4. Mirá los resultados en las diferentes pestañas
5. Si usaste PBIP, podés corregir problemas automáticamente en la pestaña "Auto-Fix"

---

## Si Necesitás Ayuda

Contactate con el Equipo de Visualización de Datos de YPF

---

**Versión 2.0**
