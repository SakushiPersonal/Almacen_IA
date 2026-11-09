1.- levantar pytest con modulo health:
        No funciona, ya que al hacer todas las importanciones necesarias se llama a una session de la base de datos, la cual a su vez llama las variables settings desde config.py, las cuales 'BaseSettings' sirve para encontrarlas, pero aún no está configurado para encontrarlas desde el .env, lo cual hace que falle el test por no encontrar valor para la variable 'DATABASE_URL'

2.- Estar más ateto al código que recivo de plantillas y ayudas externas:
        Tanto de los comentarios como la estructura y funciones de cuertos módulos que no existen, tener coherencia en el código escrito y en los comentarios. Código que no entiendas que hace no es tú código.

3.- existen funciones que cuando les entregas un texto como ruta, hay que tener cuidado, ya que si usamos una ruta relativa para encontrar un archivo, hay que considerar desde donde se ejecutó el comando/función, ésto definirá si se encontrará el archivo o no.
EJ: catalog = open("catalog.csv").read()

4.- Al importar un archivo py como módulo, se importa todo el módulo, incluso si es que se especifica importar una clase o función específica. Esto NO quiere decir que todo el código del módulo se ejecutará, solo se ejecutará aquello que esté a nivel módulo (variables, prints, llamados de funciones directas), todo lo demás no se ejecutará, pero si se importará (funciones, clases, declaración de instancias). Además el módulo solo se importa una vez, al haberse importado ya anteriormente python lo guarda en python.modules y lo rescata de allí mientras el proceso general siga funcionando.
Como buena práctica, siempre considerar construir funciones en variables (nivel módulo), solo aquellas que no requieran de consultas a datos externos; mientras que todas las demás las dejaremos a nivel función y solo las llamaremos cuando sean necesarias para evitar que se levanten excepciones por falta de argumentos al importar un módulo.

Considera que estas exepciones pueden levantarse en el siguiente orden al importarse un módulo:
        1.- Python verifica todo el módulo y se asegura de que todo esté en orden (estructuras, arguemntos, otros).
        2.- Se ejecuta en orden todo aquello que esté a nivel módulo.
        3.- cada funcion o clase que se ejecuté verificará internamente sus argumentos y datos necesarios para funcionar.

5.- Ten en cuenta que aveces que pueden definir funciones que devuelven una clase para instanciar un objeto y no un objeto en sí. En estos casos hay que hacer una doble ejecución para que la funcion nos entregue el objeto que queremos.
Ej:
        1  async with get_sessionmaker()() as session:
                pass
        
        2 factory = get_sessionmaker()
          async with factory() as session:
                pass

6.- en caso de config, la clase BaseSettings automáticamente está configurada para leer las variables de entorno. En el repo en github se tienen que configurar en los secretos, en cambio para nuestro proyecto local lo seteamos definiendo las variables dentro de nuestro archivo .env, el cual luego docker-compose se encarga de transformarlo a variables de entorno para los distintos contenedores a los cuales se le seleccione.

        Orden de adquisición de valores:
                1.- Los argumentos que pasas al construir: Settings(database_url=...).
                2.- Las variables de entorno.
                3.- El archivo .env.
                4.- Los valores por defecto de la clase.

7.- Definición fácil de qué es un endpoint: Método HTTP (GET, POST, PUT, DELETE) + ruta (ej: /api/v1/health).

        Además la función de Python que se ejecuta al llegar este request se llama HANDLER (async def health()).

8.- Respecto a la APP, con fastAPI, no se conecta nada ni se levantan puertos, solo se Crea un Objeto en memoria con configuración y rutas, lo que realmente "levanta" la app es Uvicorn, el cual no se llega a utilizar en caso de los test, ya que usamos ASGITransport, el cual se encarga de hacer todo de forma interna en memoria, no debemos preocuparnos.

9.- lifespan: son eventos de ciclo de vida de un proceso, en nuestro caso ahora lo tenemos para nuestra APP, por lo cual quiere decir que lifespan avisa cuando la app arranca y cuando se apaga.

Por lo cual nuestra app ASGI recibe dos tipos de mensajes: los request HTTP y los eventos de lifespan.

Por lo cual nunestr app tiene dos formas de arrancar actualmente:

        Uvicorn: Éste envía los dos: 
                Arraque : avisa Startup
                requests http
                Apagado : avisa shutdown

        ASGITransport (Test): al ser de HTTPX, éste solo envía requests HTTP, por lo cuál nunca avisa a la app que se apaga o que arranca.