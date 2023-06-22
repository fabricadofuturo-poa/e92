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
  )
  from flask_wtf import FlaskForm
  import asyncio
  from configparser import ConfigParser, NoSectionError
  from jinja2 import TemplateNotFound
  import os
  import secrets
  import uvicorn
  from wtforms import (
    SelectField,
    SubmitField,
    validators,
  )
except Exception as e:
  logging.exception(e)
  sys.exit(repr(e))

config_file: str = os.path.join("config.ini")
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

class CorreioForm(FlaskForm):
  """Correio Elegante"""
  mensagem: SelectField = SelectField(
    "Selecione a mensagem",
    [validators.DataRequired()],
    choices = [("0", "Nenhuma")],
  )
  submit: SubmitField = SubmitField("Entrar")

app: Quart = Quart(__name__)
app.secret_key: str = secrets.token_urlsafe(32)

@app.route("/", defaults={"page": "index"})
@app.route("/<page>")
async def show(page):
  """Attempt to load template for `page`"""
  try:
    return await render_template(f"{page}.html")
  except TemplateNotFound as e:
    logger.warning(f"Template not found for {page}")
    return await render_template_string("""<p>Peraí que ainda não tá \
pronto o site, tchê</p>""")
  except Exception as e:
    logger.exception(e)
    return jsonify(repr(e))

@app.errorhandler(TemplateNotFound)
@app.errorhandler(404)
@app.route("/quedelhe")
async def not_found(*e: Exception) -> str:
  """404"""
  logger.exception(e)
  try:
    return await render_template_string("""<h1>Que-de-lhe&quest;</h1>\
<p>Alguém deve ter te mandado o link errado, provavelmente de \
propósito, mas existe uma possibilidade de tu ter cagado e digitado \
errado.</p><p><a href='{{url_for("login") }}'>voltar</a></p>\
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
