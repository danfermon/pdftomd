#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script auxiliar para obter um REFRESH TOKEN (permanente) do Dropbox.
Permite que o processamento rode dias e noites ininterruptamente,
renovando o token de acesso automaticamente em segundo plano.
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect

def main():
    print("\n" + "=" * 70)
    print(" OBTENÇÃO DE REFRESH TOKEN PERMANENTE DO DROPBOX (OAUTH 2.0 OFFLINE)")
    print("=" * 70)

    app_key = os.environ.get("DROPBOX_APP_KEY")
    app_secret = os.environ.get("DROPBOX_APP_SECRET")

    if not app_key or not app_secret:
        print("\nInforme os dados do seu App do Dropbox (App Console):")
        if not app_key:
            app_key = input("App Key: ").strip()
        if not app_secret:
            app_secret = input("App Secret: ").strip()
    else:
        print(f"\n[✓] App Key encontrada no .env: {app_key[:6]}...")
        print(f"[✓] App Secret encontrada no .env: {app_secret[:4]}...")

    # Cria o fluxo de autorização solicitando token 'offline' (Refresh Token)
    auth_flow = DropboxOAuth2FlowNoRedirect(
        app_key,
        app_secret,
        token_access_type='offline'
    )

    authorize_url = auth_flow.start()

    print("\n" + "-" * 70)
    print("PASSO 1: Abra o seguinte link no seu navegador para autorizar:")
    print("-" * 70)
    print(f"\n{authorize_url}\n")
    print("-" * 70)
    print("PASSO 2: Faça login, clique em 'Permitir' e copie o CÓDIGO gerado na tela.")
    print("-" * 70)

    auth_code = input("\nCole o Código de Autorização aqui: ").strip()

    if not auth_code:
        print("Código não fornecido. Cancelando.")
        sys.exit(1)

    try:
        oauth_result = auth_flow.finish(auth_code)
        refresh_token = oauth_result.refresh_token
        access_token = oauth_result.access_token

        print("\n" + "=" * 70)
        print(" SUCESSO! REFRESH TOKEN GERADO!")
        print("=" * 70)
        print(f"\nDROPBOX_REFRESH_TOKEN={refresh_token}\n")
        print("=" * 70)

        # Pergunta se quer salvar automaticamente no .env
        env_path = Path(".env")
        salvar = input("\nDeseja salvar automaticamente este REFRESH TOKEN no seu arquivo .env? (S/n): ").strip().lower()
        if salvar not in ('n', 'nao', 'não', 'no'):
            env_content = ""
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    env_content = f.read()

            if "DROPBOX_REFRESH_TOKEN" in env_content:
                # Substitui
                lines = env_content.splitlines()
                new_lines = []
                for line in lines:
                    if line.startswith("DROPBOX_REFRESH_TOKEN"):
                        new_lines.append(f"DROPBOX_REFRESH_TOKEN={refresh_token}")
                    else:
                        new_lines.append(line)
                env_content = "\n".join(new_lines) + "\n"
            else:
                env_content += f"\nDROPBOX_REFRESH_TOKEN={refresh_token}\n"

            with open(env_path, "w", encoding="utf-8") as f:
                f.write(env_content)

            print("[✓] Arquivo .env atualizado com sucesso!")

        print("\nAgora o seu sistema pode renovar tokens automaticamente para sempre.")

    except Exception as e:
        print(f"\n[ERRO] Falha ao trocar código pelo Refresh Token: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
