"""
correio.fabricadofuturo.com

Copyright 2023 Fábrica do Futuro

Licensed under the Apache License, Version 2.0 (the "License"); you may 
not use this file except in compliance with the License. You may obtain 
a copy of the License at  

http://www.apache.org/licenses/LICENSE-2.0  

Unless required by applicable law or agreed to in writing, software 
distributed under the License is distributed on an "AS IS" BASIS, 
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or 
implied.  
See the License for the specific language governing permissions and 
limitations under the License.  
"""

import logging
import sys

try:
  from quart import (
    abort,
    flask_patch,
    jsonify,
    Quart,
    render_template,
    render_template_string,
    request,
  )
  from flask_wtf import FlaskForm
  import asyncio
  from configparser import ConfigParser, NoSectionError
  from jinja2 import TemplateNotFound
  import os
  import secrets
  import uvicorn
  from wtforms import (
    RadioField,
    StringField,
    SubmitField,
    validators,
  )
  import BTrees
  import transaction
  import uuid
  import zc.zlibstorage
  import ZODB
  import ZODB.FileStorage
except Exception as e:
  logging.exception(e)
  sys.exit(repr(e))

config_file: str = os.path.join("instance", "config.ini")
zodb_path: str = os.path.join("instance", "zodb")
uvicorn_socket: str | None = None
uvicorn_host: str | None = None
uvicorn_port: str | None = None
log_level: str | None = None
responsável: str = "Responsável"

try:
  config: ConfigParser = ConfigParser()
  config.read(config_file)
  uvicorn_socket = config["uvicorn"]["socket"]
  uvicorn_host = config["uvicorn"]["host"]
  uvicorn_port = int(config["uvicorn"]["port"])
  log_level = config["uvicorn"]["log_level"]
  responsável = config["uvicorn"]["responsavel"]
except (Exception, NoSectionError) as e:
  logging.exception(e)
  sys.exit("Arquivo de configuração não existe ou tá errado")

logging.basicConfig(level = log_level.upper())
logger: logging.Logger = logging.getLogger(__name__)

async def croak_db(db: object) -> None:
  """Encerra a conexão com ZODB"""
  try:
    db.close()
  except Exception as e:
    logger.exception(e)
    logger.warning("ZODB já estava fechada")

async def croak_transaction(transaction: object) -> None:
  """Encerra transação com ZODB"""
  try:
    transaction.abort()
  except Exception as e:
    logger.exception(e)
    logger.warning("Transação já estava fechada")

async def get_db(path: str) -> None | object:
  """Retorna objeto de conexão com ZODB (compressed FileStorage)"""
  try:
    try:
      storage: object = ZODB.FileStorage.FileStorage(path)
    except FileNotFoundError:
      os.makedirs(os.path.dirname(path))
      storage: object = ZODB.FileStorage.FileStorage(path)
    compressed_storage: object = zc.zlibstorage.ZlibStorage(storage)
    db: object = ZODB.DB(compressed_storage)
    return db
  except Exception as e:
    logger.exception(e)
  return None

async def get_correios(
  *args,
  **kwargs,
) -> dict[str, None | bool | str]:
  """Retorna lista de correios"""
  _return: dict[str, str | bool | None] = {
    'status': False,
    'error': "Não deu certo",
    'exception': None,
    'data': None,
  }
  try:
    db: object = await get_db(f"{zodb_path}/correios.fs")
    if not db:
      _return['error'] = """Banco de correios não existe ou foi \
corrompido"""
      raise Exception()
    try:
      connection: object = db.open()
      root: object = connection.root
      correios: list | None = None
      try:
        correios = root.correios
        _return['data'] = [
          {k:v for (k,v) in correios[c].items()} \
          for c in correios \
        ]
        _return['error'] = "Correios recuperadas do banco de dados"
        _return['status'] = True
      except AttributeError as e2:
        _return['error'] = "Não há correios no banco de dados"
        _return['exception'] = e2
      finally:
        await croak_db(db)
    except Exception as e1:
      logger.exception(e1)
      _return['exception'] = repr(e1)
      raise
    finally:
      await croak_db(db)
  except Exception as e:
    logger.exception(e)
  return _return

async def get_correio(
  _id: str,
  *args,
  **kwargs,
) -> dict[str, None | bool | str]:
  """Retorna correio a partir de id"""
  _return: dict[str, str | bool | None] = {
    'status': False,
    'error': "Não deu certo",
    'exception': None,
    'data': None,
  }
  try:
    db: object = await get_db(f"{zodb_path}/correios.fs")
    if not db:
      _return['error'] = """Banco de correios não existe ou foi \
corrompido"""
      raise Exception()
    try:
      connection: object = db.open()
      root: object = connection.root
      correios: list | None = None
      try:
        correios = root.correios
        try:
          correio: dict = [
            correios[c] \
            for c in correios \
            if str(correios[c]['id']) == _id \
          ][0]
          _return['data'] = {k:v for (k,v) in correio.items()}
          _return['error'] = "Correio encontrado"
          _return['status'] = True
        except IndexError:
          _return['error'] = "Correio não encontrado"
        except Exception as e3:
          logger.exception(e3)
          _return['exception'] = e3
          raise
        finally:
          await croak_db(db)
      except AttributeError as e2:
        _return['error'] = "Não há correios no banco de dados"
        _return['exception'] = e2
        raise
      finally:
        await croak_db(db)
    except Exception as e1:
      logger.exception(e1)
      _return['exception'] = repr(e1)
      raise
    finally:
      await croak_db(db)
  except Exception as e:
    logger.exception(e)
  return _return

async def set_correio(
  de: str,
  para: str,
  mensagem: str,
  *args,
  **kwargs,
) -> dict[str, None | bool | str | object]:
  """Insere correio novo no banco de dados"""
  _return: dict[str, str | bool | None] = {
    'status': False,
    'error': "Não deu certo",
    'exception': None,
    'data': None,
  }
  try:
    db: object = await get_db(f"{zodb_path}/correios.fs")
    if not db:
      _return['error'] = """Banco de correios não existe ou foi \
corrompido"""
      raise Exception()
    try:
      connection: object = db.open()
      root: object = connection.root
      correios: list | None = None
      try:
        correios = root.correios
      except AttributeError:
        root.correios = BTrees.OOBTree.OOBTree()
        correios = root.correios
      try:
        _id: str = str(uuid.uuid4())
        correios[_id] = BTrees.OOBTree.OOBTree()
        correio = correios[_id]
        correio['id'] = _id
        correio['de'] = de
        correio['para'] = para
        correio['mensagem'] = mensagem
        transaction.commit()
      except Exception as e3:
        await croak_transaction(transaction)
        logger.exception(e3)
        _return['exception'] = repr(e3)
        raise
      finally:
        await croak_db(db)
      _return['error'] = "Correio inserido no banco de dados"
      _return['status'] = True
    except Exception as e1:
      logger.exception(e1)
      _return['exception'] = repr(e1)
      raise
    finally:
      await croak_db(db)
  except Exception as e:
    logger.exception(e)
  return _return

async def get_all_mensagens(
  *args,
  **kwargs,
) -> dict[str, None | bool | str]:
  """Retorna dicionário de mensagens"""
  _return: dict[str, str | bool | None] = {
    'status': False,
    'error': "Não deu certo",
    'exception': None,
    'data': None,
  }
  try:
    db: object = await get_db(f"{zodb_path}/mensagens.fs")
    if not db:
      _return['error'] = """Banco de mensagens não existe ou foi \
corrompido"""
      raise Exception()
    try:
      connection: object = db.open()
      root: object = connection.root
      mensagens: list | None = None
      try:
        mensagens = root.mensagens
        _return['data'] = {
          k:{sk:sv for (sk,sv) in v.items()} \
          for (k,v) in mensagens.items() \
        }
        _return['error'] = "Mensagens recuperadas do banco de dados"
        _return['status'] = True
      except AttributeError as e2:
        _return['error'] = "Não há mensagens no banco de dados"
        _return['exception'] = e2
      finally:
        await croak_db(db)
    except Exception as e1:
      logger.exception(e1)
      _return['exception'] = repr(e1)
      raise
    finally:
      await croak_db(db)
  except Exception as e:
    logger.exception(e)
  return _return

async def get_mensagens(
  *args,
  **kwargs,
) -> dict[str, None | bool | str]:
  """Retorna lista de mensagens"""
  _return: dict[str, str | bool | None] = {
    'status': False,
    'error': "Não deu certo",
    'exception': None,
    'data': None,
  }
  try:
    db: object = await get_db(f"{zodb_path}/mensagens.fs")
    if not db:
      _return['error'] = """Banco de mensagens não existe ou foi \
corrompido"""
      raise Exception()
    try:
      connection: object = db.open()
      root: object = connection.root
      mensagens: list | None = None
      try:
        mensagens = root.mensagens
        _return['data'] = [
          {k:v for (k,v) in mensagens[m].items()} \
          for m in mensagens \
        ]
        _return['error'] = "Mensagens recuperadas do banco de dados"
        _return['status'] = True
      except AttributeError as e2:
        _return['error'] = "Não há mensagens no banco de dados"
        _return['exception'] = e2
      finally:
        await croak_db(db)
    except Exception as e1:
      logger.exception(e1)
      _return['exception'] = repr(e1)
      raise
    finally:
      await croak_db(db)
  except Exception as e:
    logger.exception(e)
  return _return

async def get_mensagem(
  _id: str,
  *args,
  **kwargs,
) -> dict[str, None | bool | str]:
  """Retorna caminho de arquivo de mensagem a partir de id"""
  _return: dict[str, str | bool | None] = {
    'status': False,
    'error': "Não deu certo",
    'exception': None,
    'data': None,
  }
  try:
    db: object = await get_db(f"{zodb_path}/mensagens.fs")
    if not db:
      _return['error'] = """Banco de mensagens não existe ou foi \
corrompido"""
      raise Exception()
    try:
      connection: object = db.open()
      root: object = connection.root
      mensagens: list | None = None
      try:
        mensagens = root.mensagens
        try:
          mensagem: dict = [
            mensagens[m] \
            for m in mensagens \
            if str(mensagens[m]['id']) == _id \
          ][0]
          _return['data'] = {k:v for (k,v) in mensagem.items()}
          _return['error'] = "Mensagem encontrada"
          _return['status'] = True
        except IndexError:
          _return['error'] = "Mensagem não encontrada"
        except Exception as e3:
          logger.exception(e3)
          _return['exception'] = e3
          raise
        finally:
          await croak_db(db)
      except AttributeError as e2:
        _return['error'] = "Não há mensagens no banco de dados"
        _return['exception'] = e2
        raise
      finally:
        await croak_db(db)
    except Exception as e1:
      logger.exception(e1)
      _return['exception'] = repr(e1)
      raise
    finally:
      await croak_db(db)
  except Exception as e:
    logger.exception(e)
  return _return

async def set_mensagem(
  path: str,
  description: str,
  *args,
  **kwargs,
) -> dict[str, None | bool | str | object]:
  """Insere mensagem nova no banco de dados"""
  _return: dict[str, str | bool | None] = {
    'status': False,
    'error': "Não deu certo",
    'exception': None,
    'data': None,
  }
  try:
    db: object = await get_db(f"{zodb_path}/mensagens.fs")
    if not db:
      _return['error'] = """Banco de mensagens não existe ou foi \
corrompido"""
      raise Exception()
    try:
      connection: object = db.open()
      root: object = connection.root
      mensagens: list | None = None
      try:
        mensagens = root.mensagens
      except AttributeError:
        root.mensagens = BTrees.OOBTree.OOBTree()
        mensagens = root.mensagens
      if len([
        m \
        for m in mensagens \
        if mensagens[m]['path'] == path \
      ]) > 0:
        _return["status"] = True
        _return["error"] = "Mensagem já está no banco de dados"
      else:
        try:
          _id: str = str(uuid.uuid4())
          mensagens[_id] = BTrees.OOBTree.OOBTree()
          mensagem = mensagens[_id]
          mensagem['id'] = _id
          mensagem['path'] = path
          mensagem['description'] = description
          transaction.commit()
        except Exception as e3:
          await croak_transaction(transaction)
          logger.exception(e3)
          _return['exception'] = repr(e3)
          raise
        finally:
          await croak_db(db)
        _return['error'] = "Mensagem inserida no banco de dados"
        _return['status'] = True
    except Exception as e1:
      logger.exception(e1)
      _return['exception'] = repr(e1)
      raise
    finally:
      await croak_db(db)
  except Exception as e:
    logger.exception(e)
  return _return

class CorreioForm(FlaskForm):
  """Correio Elegante"""
  de: StringField = StringField(
    "De (opcional)",
    # ~ default = "não interessa",
  )
  para: StringField = StringField(
    "Para",
    [validators.DataRequired()],
    # ~ default = "Alguém",
  )
  mensagem: RadioField = RadioField(
    "Selecione a mensagem",
    [validators.DataRequired()],
    choices = [("0", "Nenhuma")],
  )
  submit: SubmitField = SubmitField("Enviar")
  async def validate_mensagem(form, field, mensagens) -> None:
    """Popula as mensagens pelo banco de dados"""
    field.choices = [
      (str(mensagem["id"]), mensagem["description"]) \
      for mensagem in \
      mensagens \
    ]

class MensagemForm(FlaskForm):
  """Cadastrar mensagem"""
  path: StringField = StringField(
    "Nome do arquivo",
    [validators.DataRequired()],
    default = "imagem.png",
  )
  description: StringField = StringField(
    "Transcrição do texto",
    [validators.DataRequired()],
    default = "kkk",
  )
  submit: SubmitField = SubmitField("Cadastrar")

app: Quart = Quart(__name__)
app.secret_key: str = secrets.token_urlsafe(32)

@app.route("/", methods = ['GET', 'POST'])
# ~ @login_required
async def correio() -> str:
  """Correio Elegante"""
  error: str | None = None
  exception: str | None = None
  mensagens: list[dict[str, str]] | None = None
  all_mensagens: dict[str, dict] | None = None
  form: FlaskForm | None = None
  try:
    _return: dict[str, None | bool | str] = await get_mensagens()
    if _return["status"]:
      mensagens = _return["data"]
    else:
      error = _return["error"]
      exception = _return["exception"]
      raise Exception(exception)
    _return: dict[str, None | bool | str] = await get_all_mensagens()
    if _return["status"]:
      all_mensagens = _return["data"]
    else:
      error = _return["error"]
      exception = _return["exception"]
    form = CorreioForm(formdata = await request.form)
    if request.method == "POST":
      form = CorreioForm()
      await form.validate_mensagem(form.mensagem, mensagens)
      try:
        _return: dict[str, None | bool | str] = await set_correio(
          form["de"].data,
          form["para"].data,
          form["mensagem"].data,
        )
        error = _return["error"]
        if _return["exception"]:
          exception = _return["exception"]
      except Exception as e:
        logger.exception(e)
        exception = repr(e)
    else:
      await form.validate_mensagem(form.mensagem, mensagens)
  except Exception as e:
    logger.exception(e)
    exception = repr(e)
  try:
    return await render_template(
      "correio.html",
      title = "Correio Elegante",
      form = form,
      error = error,
      exception = exception,
      mensagens = mensagens,
      all_mensagens = all_mensagens,
    )
  except Exception as e:
    logger.exception(e)
    return jsonify(repr(e))

@app.route("/display")
# ~ @login_required
async def display() -> str:
  """Display de mensagens"""
  error: str | None = None
  exception: str | None = None
  correios: list[dict[str, str]] | None = None
  all_mensagens: dict[str, dict] | None = None
  try:
    _return: dict[str, None | bool | str] = await get_correios()
    if _return["status"]:
      correios = _return["data"]
    else:
      error = _return["error"]
      exception = _return["exception"]
    _return: dict[str, None | bool | str] = await get_all_mensagens()
    if _return["status"]:
      all_mensagens = _return["data"]
    else:
      error = _return["error"]
      exception = _return["exception"]
  except Exception as e:
    logger.exception(e)
    exception = repr(e)
  try:
    return await render_template(
      "display.html",
      title = "Correio Elegante",
      error = error,
      exception = exception,
      correios = correios,
      all_mensagens = all_mensagens,
    )
  except Exception as e:
    logger.exception(e)
    return jsonify(repr(e))

@app.route("/mensagens", methods = ['GET', 'POST'])
# ~ @login_required
async def editar_mensagens() -> str:
  """Lista de mensagens"""
  error: str | None = None
  exception: str | None = None
  mensagens: list[dict[str, str]] | None = None
  form: FlaskForm | None = None
  try:
    form = MensagemForm(formdata = await request.form)
    if request.method == "POST":
      try:
        _return: dict[str, None | bool | str] = await set_mensagem(
          form["path"].data,
          form["description"].data,
        )
        error = _return["error"]
        if _return["exception"]:
          exception = _return["exception"]
      except Exception as e:
        logger.exception(e)
        exception = repr(e)
    _return: dict[str, None | bool | str] = await get_mensagens()
    if _return["status"]:
      mensagens = _return["data"]
    else:
      error = _return["error"]
      exception = _return["exception"]
  except Exception as e:
    logger.exception(e)
    exception = repr(e)
  try:
    return await render_template(
      "mensagens.html",
      title = "Mensagens cadastradas",
      form = form,
      error = error,
      exception = exception,
      mensagens = mensagens,
    )
  except Exception as e:
    logger.exception(e)
    return jsonify(repr(e))

@app.errorhandler(TemplateNotFound)
@app.errorhandler(404)
@app.route("/quedelhe")
async def not_found(*e: Exception) -> str:
  """404"""
  # ~ logger.exception(e)
  try:
    return await render_template_string("""<h1>Que-de-lhe&quest;</h1>\
<p>Alguém deve ter te mandado o link errado, provavelmente de \
propósito, mas existe uma possibilidade de tu ter cagado e digitado \
errado.</p><p><a href='{{url_for("correio") }}'>voltar</a></p>\
"""), 404
  except Exception as e1:
    logger.exception(e1)
    return jsonify(repr(e1))

if __name__ == '__main__':
  try:
    uvicorn.run(
      app,
      uds = uvicorn_socket,
      forwarded_allow_ips = "*",
      proxy_headers = True,
      timeout_keep_alive = 0,
      log_level = log_level.lower(),
    )
    sys.exit("TCHAU")
  except (
    OSError,
    NotImplementedError,
    asyncio.exceptions.CancelledError,
  ):
    logger.info(f"""Sistema Operacional sem suporte pra UNIX sockets. \
Usando TCP/IP""")
  try:
    uvicorn.run(
      app,
      host = uvicorn_host,
      port = uvicorn_port,
      forwarded_allow_ips = "*",
      proxy_headers = True,
      timeout_keep_alive = 0,
      log_level = log_level.lower(),
    )
    sys.exit("TCHAU")
  except Exception as e:
    logger.exception(e)
    logger.critical("Uvicorn não funcionou de jeito nenhum")
  try:
    app.run()
  except Exception as e:
    logger.exception(e)
