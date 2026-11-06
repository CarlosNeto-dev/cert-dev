"""Testes do site. Rode com: pytest"""
import pytest

import app as certdev


@pytest.fixture
def client():
    certdev.app.config["TESTING"] = True
    with certdev.app.test_client() as client:
        yield client


@pytest.mark.parametrize("path", ["/", "/sobre-equipe", "/certifications/aws",
                                  "/certifications/google_analytics", "/certifications/pcep", "/gemini"])
def test_paginas_abrem(client, path):
    assert client.get(path).status_code == 200


def test_css_e_imagens_sao_servidos(client):
    assert client.get("/static/css/style.css").status_code == 200
    assert client.get("/static/img/gemini_simbolo.png").status_code == 200


def test_pergunta_vazia_mostra_aviso(client):
    resposta = client.post("/gemini", data={"question": "   "})
    assert "Por favor, digite uma pergunta!" in resposta.get_data(as_text=True)


def test_sem_chave_o_site_nao_quebra(client, monkeypatch):
    monkeypatch.setattr(certdev, "get_client", lambda: None)
    resposta = client.post("/gemini", data={"question": "O que é PCEP?"})
    assert resposta.status_code == 200
    assert "indisponível" in resposta.get_data(as_text=True)


def test_resposta_vira_html_e_bloqueia_script(client, monkeypatch):
    monkeypatch.setattr(certdev, "get_client", lambda: object())
    monkeypatch.setattr(certdev, "ask_gemini",
                        lambda q: "**PCEP** é uma certificação de Python.\n\n<script>alert(1)</script>")
    pagina = client.post("/gemini", data={"question": "O que é PCEP?"}).get_data(as_text=True)
    assert "<strong>PCEP</strong>" in pagina
    assert "<script>alert(1)</script>" not in pagina


def test_erro_do_gemini_nao_aparece_para_o_visitante(client, monkeypatch):
    def falha(q):
        raise ValueError("detalhe interno com a chave XYZ")
    monkeypatch.setattr(certdev, "get_client", lambda: object())
    monkeypatch.setattr(certdev, "ask_gemini", falha)
    pagina = client.post("/gemini", data={"question": "Oi"}).get_data(as_text=True)
    assert "Não foi possível responder agora" in pagina
    assert "XYZ" not in pagina
