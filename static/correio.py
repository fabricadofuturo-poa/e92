"""Contador"""

import logging
logging.basicConfig(level = logging.WARNING)
logger = logging.getLogger(__name__)

try:
  import asyncio
  # ~ from datetime import datetime, timedelta
  import js
  from js import document
  import pyodide
  from pyodide import http
  from pyodide.ffi import create_proxy
  # ~ import time
except Exception as e:
  logger.exception(e)

async def atualiza_correios(*args, **kwargs) -> None:
  """Atualiza correios com o banco de dados"""
  try:
    global all_mensagens, correios, active_correios, display_correios
    api_response: object = await http.pyfetch(api_correios)
    if api_response.status:
      response: dict[str] = await api_response.json()
      correios = response['data']
      index: int = active_correios.index(True)
      active_correios = [False for c in range(len(correios))]
      active_correios[index] = True
      display_correios.element.innerText = ""
      # ~ logger.info(f"all_mensagens = {all_mensagens}")
      # ~ logger.info(f"correios = {correios}")
      for i, correio in enumerate(correios):
        correio_div: Element = document.createElement("div")
        correio_div.classList.add("carousel-item")
        correio_div.id = f"correio-{i}"
        if i == index:
          correio_div.classList.add("active")
        correio_img: Element = document.createElement("img")
        correio_img.classList.add("d-block")
        correio_img.classList.add("w-100")
        correio_img.src = base_img_url + \
          all_mensagens[correio['mensagem']]['path']
        correio_img.alt = \
          all_mensagens[correio['mensagem']]['description']
        correio_caption: Element = document.createElement("div")
        correio_caption.classList.add("carousel-caption")
        correio_caption.classList.add("d-none")
        correio_caption.classList.add("d-md-block")
        if correio.get('de') not in ['', ' ', None]:
          correio_de: Element = document.createElement("h4")
          correio_de.innerText = f"De: {correio['de']}"
          correio_caption.appendChild(correio_de)
        correio_para: Element = document.createElement("h4")
        correio_para.innerText = f"Para: {correio['para']}"
        correio_caption.appendChild(correio_para)
        correio_div.appendChild(correio_img)
        correio_div.appendChild(correio_caption)
        display_correios.element.appendChild(correio_div)
  except Exception as e:
    logger.exception(e)
    pass

async def gira_correios(*args, **kwargs) -> None:
  """Gira carrosel"""
  try:
    global active_correios
    index: int = active_correios.index(True)
    active_correios[index] = False
    try:
      active_correios[index + 1] = True
    except IndexError:
      active_correios[0] = True
    for i, correio in enumerate(active_correios):
      correio_div: Element = Element(f"correio-{i}")
      correio_div.element.classList.remove("active")
    correio_active_div: Element = Element(f"correio-{index}")
    correio_active_div.element.classList.add("active")
  except Exception as e:
    logger.exception(e)
    pass

try:
  active_correios: list[bool] = [False for c in range(len(correios))]
  active_correios[0] = True
  display_correios: Element = Element("display_correios");
  asyncio.ensure_future(
    atualiza_correios(),
    loop = asyncio.get_running_loop(),
  )
  atualiza_proxy: object = create_proxy(atualiza_correios)
  atualiza_interval: int = js.setInterval(atualiza_proxy, int(1e4))
  gira_proxy: object = create_proxy(gira_correios)
  gira_interval: int = js.setInterval(gira_proxy, int(6e3))
except Exception as e:
  logger.exception(e)
