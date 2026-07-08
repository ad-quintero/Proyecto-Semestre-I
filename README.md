# UMA Casino

Desarrollado como proyecto final del primer semestre de programación de la Universidad Monteavila (marzo-julio 2026) bajo la dirección del profesor Ernesto Lugo.

# Arquitectura

- **Lenguaje principal:** Python 3.14.6
- **Lenguajes secundarios:** HTML, CSS, Javascript
- **Plataforma principal de desarrollo:** Arch Linux (kernel 7.0.14-arch1-1)
- **Librerías externas:** Pytest, nicegui.

Este proyecto esta enfocado en una arquitectura de programación orientada a objetos. Cada juego, jugador, carta y pieza es una clase única con funcionalidad específica. En adición, para la comunicación efectiva entre distintos componentes del sistema se utiliza un modelo de programación orientada a eventos donde un sistema se puede suscribir a eventos específicos de otro sistema para reaccionar acordemente.

**RECOMENDACIÓN:** No analizar el código de los renderizadores. Python no está hecho para desarrollar GUI. La interfaz gráfica se mantiene de pie por pura fuerza de voluntad e intervención divina del universo.

# Como Ejecutar

1. Clonar este repositorio.
2. Crear y activar un virtual environment.
    - **Windows (Powershell):** `python -m venv venv; .\venv\Scripts\activate.ps1`
    - **Windows (cmd):** `python -m venv venv && .\venv\Scripts\activate.bat`
    - **Linux y MacOS:** `python3 -m venv venv && source venv/bin/activate`
3. Instalar dependencias `pip install -r requirements.txt`
4. Instalar este proyecto como dependencia `pip install .`. Ejecutar con el argumento _editable_ si se desean hacer cambios al código `pip install -e .`.
5. Ejecutar `python main.py`.

**Advertencia:** Por razones de seguridad y privacidad los buscadores modernos [no permiten reproducción de audio automática](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay). Si se desea reproducir la música de fondo de la página esta debe ser ser manualmente autorizada.
