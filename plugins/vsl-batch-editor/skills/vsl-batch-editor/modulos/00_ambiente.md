# Módulo: ambiente (Mac sem admin)
Rodar uma vez por Mac; tudo vai para a conta do usuário, sem senha.
```
python3 -m pip install --user imageio-ffmpeg numpy faster-whisper pillow
mkdir -p ~/bin && ln -sf "$(python3 -c 'import imageio_ffmpeg as m;print(m.get_ffmpeg_exe())')" ~/bin/ffmpeg
grep -q 'HOME/bin' ~/.zshrc || echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
```
- `ffprobe`: o pacote não traz. `cp "<raiz>/_FLUXO_VSL/scripts/ffprobe" ~/bin/ && chmod +x ~/bin/ffprobe` (script Python
  que lê a duração com `ffmpeg -i`) — o `vsl.py` só usa `ffprobe -show_entries format=duration`. O `fluxo.py` não precisa dele.
- Rodar os scripts com `python3` normal (não `python3 -I`, que esconde o numpy instalado com `--user`).
- O faster-whisper baixa o modelo `small` na primeira transcrição (~460 MB).
- Homebrew exige admin: não usar.
