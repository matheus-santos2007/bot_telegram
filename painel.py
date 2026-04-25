import tkinter as tk
from tkinter import messagebox
import json
import os
import re
import requests

# ==========================
# CONFIG
# ==========================
TOKEN = "8364890279:AAF-nBW9feXbxg6EgSY09SZwlibWmKpAShE"

ARQ_GRUPOS = "grupos.json"
ARQ_HISTORICO = "historico.json"


# ==========================
# JSON Utils
# ==========================
def carregar_json(nome, padrao):
    if os.path.exists(nome):
        try:
            with open(nome, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return padrao
    return padrao


def salvar_json(nome, dados):
    with open(nome, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)


# ==========================
# Telegram API
# ==========================
def enviar_mensagem(chat_id, texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "Markdown"
    }
    r = requests.post(url, data=payload)
    return r.status_code == 200


# ==========================
# Shopee Utils
# ==========================
def link_eh_shopee(url: str) -> bool:
    return "shopee.com" in url.lower() or "s.shopee.com.br" in url.lower()


def validar_preco(preco: str):
    match = re.search(r"(\d{1,5}[.,]\d{2})", preco)
    if match:
        return match.group(1).replace(".", ",")
    return None


# ==========================
# UI Helpers
# ==========================
def set_status(msg):
    status_label.config(text=msg)
    janela.update_idletasks()


def carregar_listas():
    grupos = carregar_json(ARQ_GRUPOS, [])
    historico = carregar_json(ARQ_HISTORICO, [])

    lista_grupos.delete(0, tk.END)
    for g in grupos:
        lista_grupos.insert(tk.END, f"{g['nome']}  ({g['id']})")

    lista_historico.delete(0, tk.END)
    for h in historico[-30:]:
        lista_historico.insert(tk.END, h)

    set_status("Listas atualizadas.")


def gerar_mensagem():
    titulo = entry_titulo.get().strip()
    preco = entry_preco.get().strip()
    link = entry_link.get().strip()

    if not titulo:
        return None

    preco_ok = validar_preco(preco)

    msg = f"🔥 *OFERTA SHOPEE* 🔥\n\n"
    msg += f"🛒 *{titulo}*\n\n"

    if preco_ok:
        msg += f"💰 *Preço:* R$ {preco_ok}\n\n"

    if link.startswith("http"):
        msg += f"👉 *Link para comprar:*\n{link}\n\n"

    msg += "⚡ Promoção por tempo limitado!"

    return msg


def atualizar_preview():
    msg = gerar_mensagem()
    preview_text.delete("1.0", tk.END)
    if msg:
        preview_text.insert(tk.END, msg)


def copiar_preview():
    msg = preview_text.get("1.0", tk.END).strip()
    if not msg:
        messagebox.showwarning("Aviso", "Nada para copiar.")
        return

    janela.clipboard_clear()
    janela.clipboard_append(msg)
    set_status("Mensagem copiada para a área de transferência.")


def limpar_historico():
    if messagebox.askyesno("Confirmar", "Deseja apagar TODO o histórico?"):
        salvar_json(ARQ_HISTORICO, [])
        carregar_listas()
        set_status("Histórico apagado.")


def postar_oferta():
    titulo = entry_titulo.get().strip()
    preco = entry_preco.get().strip()
    link = entry_link.get().strip()

    if not titulo:
        messagebox.showerror("Erro", "Digite o título do produto.")
        return

    preco_ok = validar_preco(preco)
    if not preco_ok:
        messagebox.showerror("Erro", "Preço inválido. Exemplo: 40,90")
        return

    if not link.startswith("http"):
        messagebox.showerror("Erro", "Digite um link válido.")
        return

    if not link_eh_shopee(link):
        messagebox.showerror("Erro", "Somente links da Shopee são aceitos.")
        return

    grupos = carregar_json(ARQ_GRUPOS, [])
    historico = carregar_json(ARQ_HISTORICO, [])

    if not grupos:
        messagebox.showerror("Erro", "Nenhum grupo cadastrado no grupos.json.")
        return

    if link in historico:
        messagebox.showwarning("Aviso", "Esse link já foi postado antes.")
        return

    mensagem = f"""🔥 *OFERTA SHOPEE* 🔥

🛒 *{titulo}*

💰 *Preço:* R$ {preco_ok}

👉 *Link para comprar:*
{link}

⚡ Promoção por tempo limitado!
"""

    set_status("Enviando oferta... aguarde.")

    enviados = 0
    falhas = 0

    for g in grupos:
        ok = enviar_mensagem(g["id"], mensagem)
        if ok:
            enviados += 1
        else:
            falhas += 1

    historico.append(link)
    salvar_json(ARQ_HISTORICO, historico)

    carregar_listas()

    set_status(f"Enviado para {enviados} grupo(s). Falhas: {falhas}")

    messagebox.showinfo("Sucesso", f"Oferta enviada!\n\n✅ Enviados: {enviados}\n❌ Falhas: {falhas}")

    entry_titulo.delete(0, tk.END)
    entry_preco.delete(0, tk.END)
    entry_link.delete(0, tk.END)
    preview_text.delete("1.0", tk.END)


# ==========================
# Tkinter Layout (Dark UI)
# ==========================
janela = tk.Tk()
janela.title("Painel Shopee Bot PRO")
janela.geometry("980x600")
janela.resizable(False, False)

# Colors
BG = "#0f172a"
CARD = "#1e293b"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"
BTN = "#7c3aed"
BTN2 = "#22c55e"
DANGER = "#ef4444"

janela.configure(bg=BG)

# Top Title
title = tk.Label(
    janela,
    text="🛒 Painel Shopee Bot PRO",
    font=("Segoe UI", 20, "bold"),
    bg=BG,
    fg=TEXT
)
title.pack(pady=12)

subtitle = tk.Label(
    janela,
    text="Poste ofertas automaticamente nos seus grupos cadastrados",
    font=("Segoe UI", 11),
    bg=BG,
    fg=MUTED
)
subtitle.pack(pady=2)


# Main container
main_frame = tk.Frame(janela, bg=BG)
main_frame.pack(fill="both", expand=True, padx=15, pady=15)

left = tk.Frame(main_frame, bg=CARD, padx=15, pady=15)
left.place(x=0, y=0, width=480, height=480)

right = tk.Frame(main_frame, bg=CARD, padx=15, pady=15)
right.place(x=495, y=0, width=470, height=480)

# Left - Form
form_title = tk.Label(left, text="📌 Criar Oferta", font=("Segoe UI", 14, "bold"), bg=CARD, fg=TEXT)
form_title.pack(anchor="w", pady=(0, 10))

tk.Label(left, text="Título do Produto", font=("Segoe UI", 10), bg=CARD, fg=MUTED).pack(anchor="w")
entry_titulo = tk.Entry(left, font=("Segoe UI", 11), bg="#0b1220", fg=TEXT, insertbackground=TEXT, relief="flat")
entry_titulo.pack(fill="x", pady=(4, 10), ipady=8)

tk.Label(left, text="Preço (ex: 40,90)", font=("Segoe UI", 10), bg=CARD, fg=MUTED).pack(anchor="w")
entry_preco = tk.Entry(left, font=("Segoe UI", 11), bg="#0b1220", fg=TEXT, insertbackground=TEXT, relief="flat")
entry_preco.pack(fill="x", pady=(4, 10), ipady=8)

tk.Label(left, text="Link Shopee", font=("Segoe UI", 10), bg=CARD, fg=MUTED).pack(anchor="w")
entry_link = tk.Entry(left, font=("Segoe UI", 11), bg="#0b1220", fg=TEXT, insertbackground=TEXT, relief="flat")
entry_link.pack(fill="x", pady=(4, 12), ipady=8)

btn_frame = tk.Frame(left, bg=CARD)
btn_frame.pack(fill="x", pady=10)

btn_preview = tk.Button(
    btn_frame, text="👁 Atualizar Preview", font=("Segoe UI", 10, "bold"),
    bg=BTN, fg="white", relief="flat", command=atualizar_preview
)
btn_preview.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=8)

btn_copy = tk.Button(
    btn_frame, text="📋 Copiar Mensagem", font=("Segoe UI", 10, "bold"),
    bg="#334155", fg="white", relief="flat", command=copiar_preview
)
btn_copy.pack(side="left", fill="x", expand=True, padx=(6, 0), ipady=8)

btn_post = tk.Button(
    left, text="🚀 POSTAR OFERTA", font=("Segoe UI", 12, "bold"),
    bg=BTN2, fg="white", relief="flat", command=postar_oferta
)
btn_post.pack(fill="x", pady=12, ipady=10)

# Preview Box
tk.Label(left, text="📝 Preview da Mensagem", font=("Segoe UI", 10, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
preview_text = tk.Text(left, height=9, font=("Consolas", 10), bg="#0b1220", fg=TEXT, insertbackground=TEXT, relief="flat")
preview_text.pack(fill="both", expand=True, pady=(6, 0))


# Right - Groups & History
right_title = tk.Label(right, text="📊 Controle", font=("Segoe UI", 14, "bold"), bg=CARD, fg=TEXT)
right_title.pack(anchor="w", pady=(0, 10))

# Groups list
tk.Label(right, text="👥 Grupos cadastrados", font=("Segoe UI", 10, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
lista_grupos = tk.Listbox(right, height=7, bg="#0b1220", fg=TEXT, font=("Segoe UI", 10), relief="flat")
lista_grupos.pack(fill="x", pady=(6, 12))

# History list
tk.Label(right, text="🕘 Últimos links postados", font=("Segoe UI", 10, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
lista_historico = tk.Listbox(right, height=10, bg="#0b1220", fg=TEXT, font=("Segoe UI", 10), relief="flat")
lista_historico.pack(fill="both", expand=True, pady=(6, 12))

# Buttons
right_btns = tk.Frame(right, bg=CARD)
right_btns.pack(fill="x")

btn_refresh = tk.Button(
    right_btns, text="🔄 Atualizar Listas", font=("Segoe UI", 10, "bold"),
    bg=BTN, fg="white", relief="flat", command=carregar_listas
)
btn_refresh.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=8)

btn_clear = tk.Button(
    right_btns, text="🗑 Limpar Histórico", font=("Segoe UI", 10, "bold"),
    bg=DANGER, fg="white", relief="flat", command=limpar_historico
)
btn_clear.pack(side="left", fill="x", expand=True, padx=(6, 0), ipady=8)


# Status Bar
status_label = tk.Label(
    janela,
    text="Pronto.",
    font=("Segoe UI", 10),
    bg=BG,
    fg=MUTED,
    anchor="w"
)
status_label.pack(fill="x", padx=15, pady=(0, 10))

# Auto update preview
entry_titulo.bind("<KeyRelease>", lambda e: atualizar_preview())
entry_preco.bind("<KeyRelease>", lambda e: atualizar_preview())
entry_link.bind("<KeyRelease>", lambda e: atualizar_preview())

carregar_listas()
janela.mainloop()