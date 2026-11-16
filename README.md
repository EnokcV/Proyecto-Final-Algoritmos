# Simulador de Inventario y Ventas

Aplicación de escritorio (Tkinter) para gestionar inventario y registrar ventas, con persistencia local en \datos.json\.

## Requisitos
- Python 3.x
- Tkinter (incluido normalmente con Python en Windows; verificar con \python -m tkinter\)

## Ejecutar desde VS Code
1. Abrir la carpeta del proyecto en VS Code: **File > Open Folder…**
2. Seleccionar el intérprete de Python (extensión *Python* de Microsoft).
3. Abrir una terminal integrada en la raíz del proyecto y ejecutar:

   \\\ash
   python app.py
   \\\

   También puedes abrir \pp.py\ y usar **Run ▶**.

## Pruebas
\\\ash
python -m unittest discover -s tests -v
\\\

## Estructura
- \pp.py\: interfaz gráfica.
- \modelo.py\: lógica de negocio y persistencia.
- \	ests/\: pruebas unitarias.
