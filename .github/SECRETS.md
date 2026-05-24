# GitHub Secrets (Organisation Eske-IT)

Diese Secrets sind auf Organisationsebene unter `https://github.com/organizations/Eske-IT/settings/secrets/actions` angelegt und für alle Repos in der Organisation verfügbar (nur Public-Repos im Free Plan).

| Secret | Wert | Beschreibung |
|---|---|---|
| `SSH_HOST` | `213.202.218.154` | IP des VPS |
| `SSH_USER` | `root` | SSH-Benutzer |
| `SSH_KEY` | Privater SSH-Key | Angelegt via `ssh-keygen -t ed25519` |
| `SSH_PORT` | `22` | SSH-Port (Default) |

## Einrichtung (einmalig)

Damit GitHub per SSH auf den VPS zugreifen kann, muss der Public-Key auf dem VPS autorisiert sein:

```bash
ssh-copy-id root@213.202.218.154
```
