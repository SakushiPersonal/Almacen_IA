1.- levantar pytest con modulo health:
        No funcionaba, ya que teníamos llamadas a get_settings() a nivel módulo en algunos de ellos, lo cual causaba que con solo importar un módulo, se llamara get_settings(), incluso cuando no lo necesitabamos. Esto intentaba resolver los valores de las variables, las cuales no podía obtener y por lo tanto generaba un error en el código.

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

8.- Respecto a la APP, con fastAPI, no se conecta nada ni se levantan puertos, solo se Crea un Objeto en memoria con configuración y rutas, lo que realmente "levanta" la app es Uvicorn, el cual no se llega a utilizar en caso de los test, ya que usamos ASGITransport, el cual se encarga de hacer todo de forma interna en memoria, por lo cual solo hay que tner consideración con lo que tengamos dentro de lifespan, ya que aquello no correrá en nuestros tests.

9.- lifespan: son eventos de ciclo de vida de un proceso, en nuestro caso ahora lo tenemos para nuestra APP, por lo cual quiere decir que lifespan avisa cuando la app arranca y cuando se apaga.

Por lo cual nuestra app ASGI recibe dos tipos de mensajes: los request HTTP y los eventos de lifespan.

Por lo cual nunestr app tiene dos formas de arrancar actualmente:

        Uvicorn: Éste envía los dos: 
                Arraque : avisa Startup
                requests http
                Apagado : avisa shutdown

        ASGITransport (Test): al ser de HTTPX, éste solo envía requests HTTP, por lo cuál nunca avisa a la app que se apaga o que arranca.



----------------------------------------------------------------------------------------------------

## 2026-11-09 — <CI en cero no significa verde>
- Esperaba: al correr la CI esperaba que marcara exit code 0 y verde como si los test hubieran pasado, ya que no teniamos ninguno hasta el momento.
- Obtuve: En cambio recibí un exit code 5, ya que pytest no logró encontrar test los cuales correr.
- Preguntas: ¿por qué el pytest sigue fallando a pesar de no tener test que correr?
- Predicción: Pytest puede asumir que al correrse y no encontrar tests se pueda deber a un error de que no los encuentre, y no que no existan.
- Resultado: Pytest se cierra en rojo porque considera que no encontrar pruebas es un error de configuración o un fallo en el entorno.
- Decisión: evitó tapar el rojo de pytest y en cambio se implementó un test para que lo ejecutara.


## 2026-11-09 — <ValidationError>
- Esperaba: que el test solo corriera y me entregara si el test habia fallado o no.
- Obtuve: un error por código que nisiquiera estaba en el modulo de health
- Preguntas: ¿Qué fué lo que falló y por qué?
- Predicción: algo estaba llamando a get_settings() directamente y éste no poseía los valores en algunas de sus variables.
- Resultado: estabamos llamando a get_Settings() a nivel módulo, lo cual generaba que solo al importart un módulo, python lo ejecutara.
- Decisión: modificamos el código para que todas las instancias de get_Settings se encontraran dentro de una función y no llamadas directamente dentro de un módulo.


## 2026-11-09 — <get_sessionmaker>
- Esperaba: al modificar el código para que todo aquello que requiriera de elementos externos al módulo se encontrara dentro de alguna función para no ser llamado directamente, en la función para crear una session cambiamos como se ejecutaba la fábrica, lo cual debería haber funcionado.
- Obtuve: obtube un error de tipo al intentar entregarle aquella sesion a la app.
- Preguntas: ¿por pué obtuve un error de tipo si estaba entregando la sesion correctamente?
- Predicción: algo dentro del código que cambiamos había quedado mal escrito debido a un mal entendimiento de ejecución de código.
- Resultado: Resulta que estabamos entregando la fábrica de sesiones como objeto de sesion a la app, y no una sesión creada por la fabrica para que se usara debidamente.
- Decisión: Se modificó en código para que en la función ansíncrona que entrega las sesiones se ejecutara la fábrica y luego corrieramos la fábrica para quenos devolviese la sesión que necesitabamos.


## 2026-11-09 — <lifespan>
- Esperaba: que ASGITransport al correr los tests, prácticamente ejecutara todo el código relacionado con la app.
- Obtuve: Que lo único que hace es crear la app y hacerla funcioanr de forma interna.
- Preguntas: ¿Que pasaba con lifespan y el cierre correcto de los engine?
- Predicción: Se estaba ejecutando correctamente pero n ose veía.
- Resultado: ASGITransport no ejecuta lifespan, por lo cual todo lo que pueda estar dentro de él, no se levanta.
- Decisión: Solo se tomó en consideración para no dejar código necesario para el funcionamiento de la app dentro de lifespan.


## 2026-11-09 — <get_app>
- Esperaba: que al levantar los contenedores de nuestra api, funcionaran tal cual como funcionaban a l correr main.py o los tests.
- Obtuve: error al levantar el contenedor de la app.
- Preguntas: ¿ que es diferente que no está dejando levantar la app?
- Predicción: ¿ Algo había quedado mal escrito o ignorado en el dockerfile?
- Resultado:  Resulta que estabamos llamando a get_app dentro del dockerfile, cuando para levantar la app solo teniamos create_app
- Decisión: se modificó los valores que se le entregaban al dockerfile para levantar la app. Además agregamos a la CI un job para que construyera la imagen y arrancara el contenedor para evitar que el error o uno similar pueda pasar en verde otra vez.


## 2026-11-09 — <test db con error 503
- Esperaba: Esperaba que al leer los logs en el momento en el que se inicializa la app y la db, hubiera un intervalo en donde la app estuviese levantaba y la db no, por lo cual entregaría 503.
- Obtuve: solo 000 y 200
- Preguntas: ¿ está la app guardando algún estado de la db o realmente esperando a que la db esté lista para recién levantarse?
- Predicción: la app estaba esperando correctamente a que la db estuviese up antes de levantarse y hacer correr el test.
- Resultado: la db al levantarse en el contenedor, como no se había bajado con -v (volúmenes, el cual borra los datos) y no poseemos de mucho contenido en ella por el momento, ésta se estaba levantando incluso ántes que la misma app, por lo cual para cuando la app ya estaba lista para hacer el test, la base de datos ya estaba lista para recibir queries.
- Decisión: Solo se consideró el hecho y se implementó a nivel de compose que a futuro al levantar la app y la db, que la app realmente espere a que la db esté lista para recibir queries ántes de inicializarse y no solo esperar a que el contenedor de la db se levante.


## 2026-11-09 — <503 puede significar diferentes cosas, importante ver logs>
- Esperaba: al ver código de exepcion 503, la razón fiera la misma siempre.
- Obtuve: 503 tiene más de una razón por la cual se puede presentar.
- Preguntas: ¿ Donde puedo ver la razón principal detrás de una excepción 503 y porqué no son iguales?
- Predicción: al hacerse un test primero la app tiene un estado guardado y al siguiente ya reconoce que no se puede comunicar con la db.
- Resultado: Efectívamente en el primer 503 la app reconocía como conexión (pool de conexiones dentro del engine) cerrada o vencida, mientras que en el siguiente, como la conexión ya se había reconocido vencida y por lo tanto descartada, la app fué a solicitar otra y se encontró que no tenía comunicación con la db.
- Decisión: Se consideró siempre verificar los logs en caso de querer arreglar un bug entender un test, ya que en ellos aparece la verdadera razón de lo que puede estar pasando.


## 2026-11-10 — <"postgres" en healthcheck>
- Esperaba: que fuera una variable válida a entregarle al cmd para el healthcheck
- Obtuve: que para el cmd que estabamos utilizando por CMD-SHELL no hacía nada.
- Preguntas: ¿Entonces para qué es esa variable?
- Predicción: Posiblemente es para decirle al healthcheck que use postgres para hacer el test del health        
- Resultado: 'postgres' es para CMD (solo), en donde éste indica que se haga una búsqueda del servidor con nombre postgres dentro de la máquina y no dentro de el entorno/contenedor.
- Decisión: como CMD-SHELL no lo requere y no estamos buscando testear algo externo, se decidió por eliminarlo.



## 2026-11-10 — <docker compose ps, no funciona>
- Esperaba: al correr este comando, esperaba que funcionara sin problemas, ya que tenía todos lso archivos que requiere para funcionar.
- Obtuve: Obtuve un error en donde me aparecía que docker compose no existe.
- Preguntas: ¿ por qué me sale ese error, algó está mal configurado o lo estoy escribiendo mal?
- Predicción: Posiblemente se deba a la ruta desde donde lo estaba intentado ejecutar.
- Resultado: Efectivamente era por la ruta en la que no estaba intentando ejecutar, en donde no había un docker apuntando allí, ya que la ruta correcta es en la carpeta donde se encuentra el dockerfile, ya que el dockerfile apunta a esa misma carpeta como workdir.
- Decisión: se recordó la ruta para futuros casos para correr ese comando o similares de forma correcta. 



## 2026-11-10 — <Inicio, shutdown e inicio otra vez al montar la imagen de la db>
- Esperaba: Que la db si iniciara una sola vez y quedara lista.
- Obtuve: la db se inicializa una vez, luego se apaga, para que finalmente se levante otra vez y allí si queda funcionando.
- Preguntas: ¿ porqué hace eso? ¿es un comportamiento correcto o algo está saliendo mal?
- Predicción: Posiblemente se intento levantar en un intento y algo estaba mal configurado, por lo cual recurrió a cerrar el intento, levantarlo otra véz hasta que funcione (como retries).
- Resultado: Sucede que docker levanta la imagen primero apuntando a un socket Unix en donde solo el contenedor escucha, ésto para levantar la estructura de la base de datos (como el esqueleto), una vez hecho esto, guarda el esqueleto en la imagen, apaga la base de datos y levanta otra con la info guardada más los datos necesarios escuchando el los puertos IPv4 e IPv6 correspondientes para que esta db pueda ser alcanzada por otras aplicaciones.
- Decisión: Solo se registró el conocimiento y se tomó como comportamiendo estándar de como se levanta el contenedor de la base de datos.