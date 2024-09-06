import cv2

# Inicializar la cámara
cap = cv2.VideoCapture(0)

# Factor de zoom (1.0 = sin zoom, >1.0 = zoom in)
zoom_factor = 1.5

while True:
    # Capturar fotograma
    ret, frame = cap.read()

    if not ret:
        break

    # Obtener las dimensiones de la imagen
    height, width, _ = frame.shape

    # Calcular la dimensión para mantener el ratio 1:1
    if width > height:
        # Si la imagen es más ancha, recortar el ancho
        new_dim = height
    else:
        # Si la imagen es más alta, recortar el alto
        new_dim = width

    # Aplicar zoom (ajustar el área de recorte según el factor de zoom)
    zoomed_dim = int(new_dim / zoom_factor)

    # Calcular el centro y los márgenes para el recorte
    x1 = max((width - zoomed_dim) // 2, 0)
    y1 = max((height - zoomed_dim) // 2, 0)
    x2 = min((width + zoomed_dim) // 2, width)
    y2 = min((height + zoomed_dim) // 2, height)

    # Recortar la imagen para mantener el ratio 1:1 con zoom
    cropped_frame = frame[y1:y2, x1:x2]

    # Redimensionar la imagen recortada para que coincida con la resolución original
    resized_frame = cv2.resize(cropped_frame, (new_dim, new_dim))

    # Mostrar la imagen con el zoom aplicado
    cv2.imshow('Zoomed Frame (1:1 Ratio)', resized_frame)

    # Salir si se presiona la tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Liberar la captura y cerrar las ventanas
cap.release()
cv2.destroyAllWindows()
