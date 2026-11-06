"""CertDev: guia de certificações para desenvolvedores, com um assistente do Gemini.

Este arquivo é o ponto de entrada do site. Ele funciona do mesmo jeito em dois lugares:
- no computador: ``python app.py``;
- no Vercel: a plataforma encontra a variável ``app`` aqui e cria a função sozinha.
"""

import html
import logging
import os

import markdown
from dotenv import load_dotenv
from flask import Flask, render_template, request

load_dotenv()

logger = logging.getLogger(__name__)

# Os arquivos estáticos ficam em public/static. No Vercel, tudo o que está em public/
# é servido direto pela CDN; no computador, o Flask serve a mesma pasta no mesmo endereço (/static).
app = Flask(__name__, static_folder="public/static", static_url_path="/static")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_PROMPT = (
    "Você é um assistente especialista em certificações para desenvolvedores, com conhecimento "
    "sobre AWS, Google Analytics e PCEP. Responda de forma direta, didática e simples, em Markdown. "
    "Comece a resposta com um parágrafo normal, sem símbolos como ` ou # na primeira linha. "
    "Se pedirem uma tabela de preços, use '-' nos campos vazios. "
    "Evite espaços grandes entre os parágrafos. "
    "Responda no mesmo idioma da pergunta."
)

MAX_QUESTION_LENGTH = 1000

_client = None


def get_client():
    """Cria o cliente do Gemini uma vez só. Sem chave configurada, devolve None."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        from google import genai

        _client = genai.Client(api_key=api_key)
    return _client


def ask_gemini(question: str) -> str:
    """Envia a pergunta ao Gemini e devolve o texto da resposta (em Markdown)."""
    client = get_client()
    if client is None:
        raise RuntimeError("GEMINI_API_KEY não configurada.")
    from google.genai import types

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=question,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    return response.text or ""


def render_markdown(text: str) -> str:
    """Converte o Markdown da resposta em HTML com segurança.

    Antes de converter, qualquer HTML vindo do modelo é escapado. Assim, uma resposta
    com <script> aparece como texto e nunca roda no navegador de quem usa o site.
    """
    safe_text = html.escape(text, quote=False)
    return markdown.markdown(safe_text, extensions=["tables", "fenced_code", "sane_lists"])


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/sobre-equipe")
def equipe():
    return render_template("sobre_equipe.html")


@app.route("/certifications/aws")
def aws():
    return render_template("certifications/aws_cloud.html")


@app.route("/certifications/google_analytics")
def google():
    return render_template("certifications/google_analytics.html")


@app.route("/certifications/pcep")
def pcep():
    return render_template("certifications/pcep.html")


@app.route("/gemini", methods=["GET", "POST"])
def gemini_page():
    gemini_response = None
    error_message = None
    question = ""

    if request.method == "POST":
        question = (request.form.get("question") or "").strip()

        if not question:
            error_message = "Por favor, digite uma pergunta!"
        elif len(question) > MAX_QUESTION_LENGTH:
            error_message = f"A pergunta pode ter no máximo {MAX_QUESTION_LENGTH} caracteres."
        elif get_client() is None:
            error_message = "O assistente está indisponível no momento. Tente novamente mais tarde."
        else:
            try:
                gemini_response = render_markdown(ask_gemini(question))
            except Exception:
                # O detalhe técnico vai para o log do servidor, não para a tela do visitante.
                logger.exception("Falha ao consultar o Gemini")
                error_message = "Não foi possível responder agora. Tente novamente em alguns instantes."

    return render_template(
        "gemini_page.html",
        gemini_response=gemini_response,
        error_message=error_message,
        question=question,
    )


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
