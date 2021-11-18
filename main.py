from typing import List
import databases
import sqlalchemy
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import urllib

#DATABASE_URL = "sqlite:///./test.db"

host_server = os.environ.get('host_server', 'localhost')
db_server_port = urllib.parse.quote_plus(str(os.environ.get('db_server_port', '5432')))
database_name = os.environ.get('database_name', 'test')
db_username = urllib.parse.quote_plus(str(os.environ.get('db_username', 'postgres')))
db_password = urllib.parse.quote_plus(str(os.environ.get('db_password', 'govinda')))
ssl_mode = urllib.parse.quote_plus(str(os.environ.get('ssl_mode','prefer')))
DATABASE_URL = 'postgresql://{}:{}@{}:{}/{}?sslmode={}'.format(db_username, db_password, host_server, db_server_port, database_name, ssl_mode)

'postgresql://db_username:db_password@host_server:db_server_port/database_name?sslmode=prefer'


database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

notes = sqlalchemy.Table(
    "notes",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("text", sqlalchemy.String),
    sqlalchemy.Column("completed", sqlalchemy.Boolean),
)

#sqllite
'''
engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)
'''


#postgres
engine = sqlalchemy.create_engine(
    DATABASE_URL, pool_size=3, max_overflow=0
)
metadata.create_all(engine)



#Pydantic models
class NoteIn(BaseModel):
    text: str
    completed: bool

class Note(BaseModel):
    id: int
    text: str
    completed: bool

'''
Add CORS to FastAPI
In order for our REST API endpoints to be consumed in client applications such as Vue, React, 
Angular or any other Web applications that are running on other domains, we should tell our FastAPI
 to allow requests from the external callers to the endpoints of this FastAPI application.
  We can enable CORS (Cross Origin Resource Sharing) either at application level or at specific 
  endpoint level. But in this situation we will add the following lines to main.py to enable CORS 
at the application level by allowing requests from all origins specified by allow_origins=[*].

allow_origins=[*] is not recommended for Production purposes. It is recommended to 
have specified list of origins such as mentioned below.
allow_origins=['client-facing-example-app.com', 'localhost:5000']
'''

app = FastAPI(title="REST API using FastAPI PostgreSQL Async EndPoints")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

'''
Application Startup & Shutdown Events
FastAPI can be run on multiple worker process with the help of Gunicorn server 
with the help of uvicorn.workers.UvicornWorker worker class. Every worker process
 starts its instance of FastAPI application on its own Process Id. In order to ensure 
 every instance of application communicates to the database, we will connect and 
 disconnect to the database instance in the FastAPI events  startup and shutdown respectively. 
So add the following code to main.py to do that.

'''
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

'''
Create a Note using HTTP Verb POST
We will use POST HTTP Verb available as post method of FastAPI’s instance variable app 
to create/ insert a new note in our notes table.

The status code on successful creation of note will be 201. This can be seen as an argument
 status_code passed to post method which accepts integer value held by status.HTTP_201_CREATED. 
Add the following code to main.py to add a note to the table.
'''

@app.post("/notes/", response_model=Note, status_code = status.HTTP_201_CREATED)
async def create_note(note: NoteIn):
    query = notes.insert().values(text=note.text, completed=note.completed)
    last_record_id = await database.execute(query)
    return {**note.dict(), "id": last_record_id}


'''
Update Note using HTTP Verb PUT
We will use PUT HTTP Verb available as put method of FastAPI’s instance variable 
appto update / modify an existing note in our notes table. 
Add the following code to main.py to modify a note from the notes table.

'''

@app.put("/notes/{note_id}/", response_model=Note, status_code = status.HTTP_200_OK)
async def update_note(note_id: int, payload: NoteIn):
    query = notes.update().where(notes.c.id == note_id).values(text=payload.text, completed=payload.completed)
    await database.execute(query)
    return {**payload.dict(), "id": note_id}

'''
Get Paginated List of Notes using HTTP Verb GET
We will use GET HTTP Verb available as get method of FastAPI’s instance variable app 
to retrieve paginated 🗐 collection of notes available in our notes table. 
Add the following code to main.py to get list of notes from the table.

Here the skip and take arguments will define how may notes to be skipped and how many notes to be returned
 in the collection respectively. If you have a total of 13 notes in your database and if you provide 
 skip a value of 10 and take a value of 20, then only 3 notes will be returned.
 skip will ignore the value based on the identity of the collection starting from old to new.

'''
@app.get("/notes/", response_model=List[Note], status_code = status.HTTP_200_OK)
async def read_notes(skip: int = 0, take: int = 20):
    query = notes.select().offset(skip).limit(take)
    return await database.fetch_all(query)

'''
Get single Note Given its Id using HTTP Verb GET
We will again use the GET HTTP Verb available as get method of FastAPI’s instance variable app 
to retrieve a single note identified by provided id in the request as a note_id query parameter. 
Add the following code to main.py to get a note given its id.
'''

@app.get("/notes/{note_id}/", response_model=Note, status_code = status.HTTP_200_OK)
async def read_notes(note_id: int):
    query = notes.select().where(notes.c.id == note_id)
    return await database.fetch_one(query)

'''
Delete single Note Given its Id using HTTP Verb DELETE
We will use DELETE HTTP Verb available as delete method of FastAPI’s instance variable app to permanently 
delete an existing note in our notes table. 
Add the following code to main.py to wipe off the note permanently given note_id as query parameter.
'''
@app.delete("/notes/{note_id}/", status_code = status.HTTP_200_OK)
async def update_note(note_id: int):
    query = notes.delete().where(notes.c.id == note_id)
    await database.execute(query)
    return {"message": "Note with id: {} deleted successfully!".format(note_id)}

 # uvicorn --port 8000 --host 127.0.0.1 main:app --reload  
 # 

'''
 With the above command, we are invoking the call to the Uvicorn ASGI server with the following infrastructure settings.

host 127.0.0.1 means we are configuring uvicorn to run our application on the localhost of the PC. The other possible values
 for host parameter is 0.0.0.0 or localhost. 0.0.0.0 is recommended when deploying the FastAPI to production environments.
port 8000 is the port on which we want our application to run. If you have any other application or service already
 running on this port, the above command will fail to execute. In such situation, try to change it to any 
 other four digit number of your choice that is found to be freely available for the application to consume.
reload It is recommended to set this flag for the development purposes only. Enabling this flag will 
automatically restart the uvicorn server with any changes you make to your code while in development. It is obvious that, 
in case there are any run time failures, you will quickly identify those changes from the error trace that caused 
the failure of uvicorn server to restart.
main:app This follows a pattern as detailed below.
main is the module where the FastAPI is initialized. In our case, all we have is main.py at the root level. 
If you are initializing the FastAPI variable somewhere under the other directories, you need to add an __init__.py file 
and expose that module so that uvicorn can properly identify the configuration. In our case main becomes the module.
app is the name of the variable which is assigned with the instance of FastAPI. You are free to change these names but 
reflect the same syntax that follows module-name:fastapi-initialization-variable pattern.
 
 ''' 

'''
Curl Commands to perform CRUD
There are three ways to perform CRUD for FastAPI REST Endpoints.

Postman, a REST Client (in fact a lot more than a REST Client) to perform calls to REST APIs
OpenAPI User Interface accessible via /docs (Swagger UI) to perform CRUD operations by clicking Try it out button available for every end point
cURL commands via a command terminal.
If you want to explore the hardcore programmer in you, I recommend trying out cURL.
'''


'''
curl -X POST "http://localhost:8000/notes/" ^
 -H "accept: application/json" ^
 -H "Content-Type: application/json" ^
 -d "{\"text\":\"Get Groceries from the store\",\"completed\":false}"



 In the above command are commanding cURL with following args:

-X indicates the presence of one of the HTTP Verbs or HTTP Request Methods followed by URL. The values include POST, GET, PUT, DELETE, PATCH.
-H indicates header. Headers are optional unless required as specified in API specifications. Some times though they are optional, specifying wrong headers may not guarantee the expected result processed by cURL.
-d is mostly used for non GET HTTP verbs and indicates data or payload that is required by the request.
^ is a line break added just for readability. It works only on Windows OS command terminals. 
If you are on any Mac or Linux distributions, replace ^ with \ (backward slash). Alternatively, you can have
 the cURL sent in single line without having any ^ line breaks.

'''





