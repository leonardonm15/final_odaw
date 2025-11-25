from pydantic import BaseModel

class UserCreate(BaseModel):
    nome: str
    email: str
    senha: str

class UserOut(BaseModel):
    id_usuario: int
    nome: str
    email: str

class Login(BaseModel):
    email: str
    senha: str

class Musica(BaseModel):
    nome: str
    genero: str
    duracao_seg: int
    id_album: int
