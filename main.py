import json
import os
import re
import asyncio

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright


# ==========================
# CONFIG
# ==========================
import os
TOKEN = os.getenv("TOKEN")
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
# Shopee helpers
# ==========================
def link_eh_shopee(url: str) -> bool:
    return "shopee.com" in url.lower() or "s.shopee.com.br" in url.lower()


def transformar_link_afiliado(url: str) -> str:
    if "s.shopee.com.br" in url.lower():
        return url
    return f"{SEU_LINK_AFILIADO_BASE}?{url}"


def extrair_numero(valor: str):
    if not valor:
        return None
    match = re.search(r"(\d+[.,]\d{2})", valor)
    if match:
        return match.group(1).replace(",", ".")
    return None


# ==========================
# PLAYWRIGHT (ROBUSTO)
# ==========================
async def extrair_dados_shopee(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        titulo = None
        preco = None
        preco_antigo = None
        desconto = None
        imagem = None
        avaliacao = None
        frete_gratis = False

        try:
            await page.goto(url, timeout=60000)

            # espera básica (Shopee é SPA)
            await page.wait_for_timeout(5000)

            html = await page.content()

            # =====================
            # TÍTULO
            # =====================
            try:
                titulo = await page.title()
            except:
                titulo = "Oferta Shopee"

            # =====================
            # IMAGEM
            # =====================
            try:
                imagem = await page.eval_on_selector(
                    'meta[property="og:image"]',
                    "el => el.content"
                )
            except:
                imagem = None

            # =====================
            # PREÇO (MELHOR MÉTODO)
            # Shopee guarda em JSON interno
            # =====================
            json_match = re.search(r'{"price":(\d+)', html)

            if json_match:
                preco = float(json_match.group(1)) / 100

            # fallback regex visual
            if not preco:
                match = re.search(r"R\$\s?\d+[.,]\d{2}", html)
                if match:
                    preco = extrair_numero(match.group(0))

            # =====================
            # PREÇO ANTIGO
            # =====================
            old_match = re.search(r'"price_before_discount":(\d+)', html)
            if old_match:
                preco_antigo = float(old_match.group(1)) / 100

            # =====================
            # DESCONTO
            # =====================
            if preco and preco_antigo:
                try:
                    desconto = round(((preco_antigo - preco) / preco_antigo) * 100)
                except:
                    desconto = None

            # =====================
            # FRETE GRÁTIS
            # =====================
            if "frete grátis" in html.lower():
                frete_gratis = True

            # =====================
            # AVALIAÇÃO
            # =====================
            rating = re.search(r'"rating_star":([\d.]+)', html)
            if rating:
                avaliacao = rating.group(1)

        except Exception as e:
            print("Erro Playwright:", e)

        await browser.close()

        return {
            "titulo": titulo,
            "preco": preco,
            "preco_antigo": preco_antigo,
            "desconto": desconto,
            "avaliacao": avaliacao,
            "frete_gratis": frete_gratis,
            "imagem": imagem
        }


# ==========================
# FORMATADOR
# ==========================
def formatar(preco):
    if not preco:
        return None
    return f"R$ {float(preco):.2f}".replace(".", ",")


# ==========================
# RECEBER LINK
# ==========================
async def receber_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    link_match = re.search(r"(https?://\S+)", texto)
    if not link_match:
        return

    link = link_match.group(1)

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
        msg += f"\n💰 Preço: {formatar(dados['preco'])}"

    if dados["desconto"]:
        msg += f"\n🏷️ Desconto: {dados['desconto']}%"

    if dados["frete_gratis"]:
        msg += f"\n🚚 Frete grátis disponível"

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
        except:
            pass

    await update.message.reply_text("✅ Enviado!")


# ==========================
# MAIN
# ==========================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_link))

    print("Bot rodando...")
    app.run_polling()


if __name__ == "__main__":
    main()