import asyncio

import typer

from freeai.core import get_settings, load_vault, reload_settings, save_vault
from freeai.services.key_validator import validate_provider_key

app = typer.Typer(help="Configuração interativa de chaves e rede.")


@app.command(name="config")
@app.command(name="setup")
def setup() -> None:
    """Assistente simples no terminal para configurar chaves de API e rede no cofre seguro."""
    vault = load_vault()
    settings = get_settings()

    typer.secho(
        "\n🔑 FreeAI — Configuração de Chaves (Enter para manter atual):", bold=True, fg=typer.colors.BRIGHT_BLUE
    )

    keys = [
        ("gemini", "GOOGLE_API_KEY", "Google AI Studio Key"),
        ("groq", "GROQ_API_KEY", "Groq Cloud Key"),
        ("openrouter", "OPENROUTER_API_KEY", "OpenRouter Key"),
    ]

    for prov_id, env_var, label in keys:
        atual = vault.get(env_var, "")
        mascara = f"[{atual[:4]}...{atual[-4:]}]" if len(atual) > 8 else ("[Configurada]" if atual else "[Vazio]")
        nova = typer.prompt(f"  {label} {mascara}", default="", hide_input=True)
        if nova.strip():
            key_val = nova.strip()
            typer.echo(f"  Validando {label}...")
            ok, msg = asyncio.run(validate_provider_key(prov_id, key_val))
            if ok:
                typer.secho(f"  ✔ {label} válida!", fg=typer.colors.GREEN)
                vault[env_var] = key_val
                vault[f"{env_var}_VALIDATED"] = True
            else:
                typer.secho(f"  ✘ {label} falhou: {msg}", fg=typer.colors.RED)
                if typer.confirm("  Deseja salvar mesmo assim?", default=False):
                    vault[env_var] = key_val
                    vault[f"{env_var}_VALIDATED"] = False

    typer.secho("\n🌐 Configurações de Rede:", bold=True, fg=typer.colors.BRIGHT_BLUE)
    host_def = str(vault.get("HOST", settings.HOST))
    port_def = int(vault.get("PORT", settings.PORT))

    new_host = typer.prompt("  Host de vinculação", default=host_def)
    new_port = typer.prompt("  Porta HTTP", default=port_def, type=int)

    vault["HOST"] = new_host.strip()
    vault["PORT"] = new_port
    save_vault(vault)
    reload_settings()

    typer.secho("\n✅ Configurações salvas no cofre com sucesso!", fg=typer.colors.GREEN, bold=True)
