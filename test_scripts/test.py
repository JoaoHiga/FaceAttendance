banda = input('Bienvenido te interesan bandas como Metallica, .....').lower()

if banda == 'no':
    print('una lastima, esperamos tener mas pronto')

else:
    banda2 = input('Muy bien, cual te llamó más la atención?').lower()

    if banda2 == 'metallica':
        print('Esa es una banda de Thrash Metal')

    elif banda2 == 'the beatles':
        print('Esa es una banda de rock')

    elif banda2 == 'daft punk':
        print('Ese es un grupo que compone música electrónica')

    else:
        print('No tengo información de esa banda')

