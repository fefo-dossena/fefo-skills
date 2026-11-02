import sys, subprocess, numpy as np
S, B = sys.argv[1], sys.argv[2]; a0,a1,t0,t1 = map(float, sys.argv[3:7]); out_p = sys.argv[7]; SR = 32000
def dec(p, ss=None, to=None):
    a = ["ffmpeg","-v","error"] + (["-ss",str(ss)] if ss is not None else []) + (["-to",str(to)] if to is not None else []) + ["-i",p,"-ac","1","-ar",str(SR),"-f","f32le","-"]
    return np.frombuffer(subprocess.run(a,capture_output=True,check=True).stdout, np.float32).copy()
orig = dec(f"{B}/03_avatar/hold/T1_visiovance.mp4"); w = dec(f"{S}/tts_c.wav", t0, t1)
alvo = int((a1 - a0) * SR); idx = np.linspace(0, len(w) - 1, alvo); w = np.interp(idx, np.arange(len(w)), w).astype(np.float32)
seg = orig[int(a0*SR):int(a1*SR)]; rms = lambda x: np.sqrt(np.mean(x**2) + 1e-12); w *= rms(seg) / rms(w)
f = int(0.015 * SR); ramp = np.linspace(0, 1, f, dtype=np.float32)
out = orig.copy(); i0 = int(a0*SR); blk = w.copy(); base = out[i0:i0+alvo].copy()
blk[:f] = blk[:f]*ramp + base[:f]*(1-ramp); blk[-f:] = blk[-f:]*ramp[::-1] + base[-f:]*(1-ramp[::-1])
out[i0:i0+alvo] = blk; out.astype(np.float32).tofile(out_p)
