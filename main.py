import json
import os
import re
import asyncio

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from playwright.async_api import async_playwright


# ==========================
# CONFIG
# ==========================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("❌ TOKEN não encontrado no ambiente (Render Environment Variables)")

ARQ_GRUPOS = "grupos.json"
ARQ_HISTORICO = "historico.json"

SEU_LINK_AFILIADO_BASE = "https://s.shopee.com.br/AUqMGXRxpC"


# ==========================
# JSON
# ==========================
def carregar_json(nome, padrao):
    if os.path.exists(nome):
        with open(nome, "r", encoding="utf-8") as f:
            return json.load(f)
    return padrao


def salvar_json(nome, dados):
    with open(nome, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)


grupos = carregar_json(ARQ_GRUPOS, [])
historico = carregar_json(ARQ_HISTORICO, [])


# ==========================
# HELPERS
# ==========================
def link_eh_shopee(url: str) -> bool:
    return "shopee.com" in url.lower() or "s.shopee.com.br" in url.lower()


def transformar_link_afiliado(url: str) -> str:
    if "s.shopee.com.br" in url.lower():
        return url
    return f"{SEU_LINK_AFILIADO_BASE}?{url}"


def formatar_preco(valor):
    if not valor:
        return None
    try:
        return f"R$ {float(valor):.2f}".replace(".", ",")
    except:
        return None


# ==========================
# PLAYWRIGHT ROBUSTO
# ==========================
async def extrair_dados_shopee(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = await browser.new_page()

        dados = {
            "titulo": "Oferta Shopee",
            "preco": None,
            "preco_antigo": None,
            "desconto": None,
            "avaliacao": None,
            "frete_gratis": False,
            "imagem": None,
        }

        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_timeout(5000)

            html = await page.content()

            # Título
            try:
                dados["titulo"] = await page.title()
            except:
                pass

            # Imagem
            try:
                dados["imagem"] = await page.eval_on_selector(
                    'meta[property="og:image"]',
                    "el => el.content"
                )
            except:
                pass

            # PREÇO (JSON interno mais confiável)
            match = re.search(r'"price":(\d+)', html)
            if match:
                dados["preco"] = float(match.group(1)) / 100

            # PREÇO ANTIGO
            match_old = re.search(r'"price_before_discount":(\d+)', html)
            if match_old:
                dados["preco_antigo"] = float(match_old.group(1)) / 100

            # DESCONTO
            if dados["preco"] and dados["preco_antigo"]:
                try:
                    dados["desconto"] = round(
                        (1 - dados["preco"] / dados["preco_antigo"]) * 100
                    )
                except:
                    pass

            # FRETE GRÁTIS
            if "frete grátis" in html.lower():
                dados["frete_gratis"] = True

            # AVALIAÇÃO
            rating = re.search(r'"rating_star":([\d.]+)', html)
            if rating:
                dados["avaliacao"] = rating.group(1)

        except Exception as e:
            print("Erro Playwright:", e)

        await browser.close()
        return dados


# ==========================
# MENSAGEM
# ==========================
async def receber_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text

    match = re.search(r"(https?://\S+)", texto)
    if not match:
        return

    link = match.group(1)

    if not link_eh_shopee(link):
        return

    if not grupos:
        await update.message.reply_text("⚠️ Nenhum grupo cadastrado.")
        return

    dados = await extrair_dados_shopee(link)
    link_afiliado = transformar_link_afiliado(link)

    msg = f"""🔥 OFERTA SHOPEE 🔥

🛒 {dados['titulo']}
"""

    if dados["preco"]:
        msg += f"\n💰 Preço: {formatar_preco(dados['preco'])}"

    if dados["desconto"]:
        msg += f"\n🏷️ Desconto: {dados['desconto']}%"

    if dados["frete_gratis"]:
        msg += f"\n🚚 Frete grátis"

    if dados["avaliacao"]:
        msg += f"\n⭐ Avaliação: {dados['avaliacao']}"

    msg += f"""

👉 Link:
{link_afiliado}

⚡ Promoção por tempo limitado!
"""

    for g in grupos:
        try:
            await context.bot.send_message(chat_id=g["id"], text=msg)
        except Exception as e:
            print("Erro envio:", e)

    await update.message.reply_text("✅ Enviado!")


# ==========================
# START
# ==========================
def main():
    print("🚀 TOKEN carregado:", bool(TOKEN))

    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_link))

    print("🤖 Bot rodando...")
    app.run_polling()


if __name__ == "__main__":
    main()