# Biblioteca de planos da EV (Neurobella e VisioVance)

Origem: skill `neurobella-broll-list` do Matthew (colega do Fefo), adotada em 18/11/2026 ("Aplica as duas").
Lista dos planos REAIS que estas marcas vivem precisando, com a palavra de busca de cada um. Use antes de inventar cena.

**Como usar no nosso fluxo (diferente do Matthew):**
1. A palavra de busca vai primeiro no **banco da EV com `real=1`** (`05a_banco.md`, "Vídeo real primeiro"). O Matthew pula o
   banco; nós não: o Daniel abriu a aba Real footage em 18/11. Sem resultado bom: busca social/stock (só com OK do Fefo para
   baixar de fora) e, por último, IA.
2. Uma cena por frase falada: cada linha do roteiro ganha o plano que mostra AQUELA frase. Frase com mais de 3 s = 2 planos.
3. `CLIENT PACKSHOT` = frasco real (foto/vídeo da marca ou do banco). Frasco gerado por IA nunca.
4. **IA só no b-roll de mecanismo** (seção 5): dentro do olho ou do sangue, onde câmera não entra. Nada de pessoa, frasco ou
   sintoma de IA no b-roll. O avatar falando (Omni/Kling) é outra regra e segue permitido.
5. Hook: movimento no 1º quadro, 1º corte antes de 1,5 s; nunca abrir em tela de celular, polegar rolando, unboxing ou
   entrega na porta.
6. Plano novo que funcionou: acrescente aqui (slug, o que mostra, palavra de busca, id do banco se houver).

**Trava no `lint_plano.py` (18/11/2026):** soma os SEGUNDOS de b-roll real x IA pelo campo `origem` de cada cena
(`real | ia | avatar | camada`; sem ele, lê o texto de `fonte`). Real < 70% ou IA fora do mecanismo = erro em batch criada
a partir de 18/11 (antes: aviso). Cena > 3 s num plano só = aviso (ponha `"planos": 2` ou divida). Avatar fica fora da conta.
Duração da cena: `dur` ou palavras da `copy` / 2,2 (ritmo medido da VO destes ADs).

**Conferir na referência (passo 0 do `02_referencia.md`):** número de planos, plano médio, **plano mais longo**, cortes nos
primeiros 10 s, palavras por minuto e segundos real x IA. Cada trava em que o ref falha é onde o nosso AD ganha: diga isso
ao Fefo. Também: rótulo e número de cápsulas iguais em todos os planos do frasco.

**Marcar, sem reescrever:** promessa de tratar doença ("stops bleeding in your eyes"), conta de oferta que não fecha
(3 por 1 = 67%, não 80%), marca diferente da do card.

## 1. Hook — scroll stoppers

Movement at frame 0. Arresting but still about the eye or the offer. First cut before 1.5 s.
Never a phone UI, a thumb scrolling, an unboxing or a porch delivery.

| Filename slug | What we need | Search keyword |
|---|---|---|
| `hook_eye-macro-blink` | EXTREME macro of a human eye filling the frame, one slow blink | `extreme close up human eye macro blink` |
| `hook_glasses-off-rub` | 60+ woman yanks her glasses off and rubs both eyes hard | `elderly woman taking off glasses rubbing eyes` |
| `hook_pill-pile-sweep` | Hand sweeps a pile of old eye-vitamin bottles aside across a table | `pile of pill bottles on table` |
| `hook_fog-wipe` | Hand wipes fog off glass, the world behind it snaps clear | `wiping fog off window hand` |
| `hook_phoropter-click` | Phoropter swinging in front of a face, lenses clicking over the eye | `phoropter eye exam lens change` |
| `hook_pupil-dilate` | Macro pupil contracting as a light passes over it | `pupil dilating close up macro` |
| `hook_eyechart-snap` | Eye chart out of focus, snapping sharp | `eye chart blurry to focus` |
| `hook_bottles-land` | Three bottles land hard on the counter in one move, low angle | CLIENT PACKSHOT |
| `hook_bottle-label-turn` | Hand picks one up, rotates the label to camera | CLIENT PACKSHOT |
| `hook_bottle-slide` | Bottle sliding across a kitchen counter toward camera | CLIENT PACKSHOT |

## 2. Symptoms — one shot per symptom the script actually names

The client's standing complaint: symptoms get said and never shown.

| Filename slug | What we need | Search keyword |
|---|---|---|
| `sympt_dirty-window` | Rain-streaked window, the street behind unreadable | `rain streaked window blurry street` |
| `sympt_headlight-glare` | Oncoming headlight glare through a windshield at night, POV | `night driving headlight glare windshield pov` |
| `sympt_squint-label` | 60+ woman holding a bottle at arm's length, squinting at small print | `senior squinting reading label` |
| `sympt_glasses-wipe` | Hand wiping eyeglasses on a shirt hem | `cleaning glasses on shirt close up` |
| `sympt_floaters-sky` | Dust specks drifting across a bright sky or sunbeam | `dust particles floating sunbeam slow motion` |
| `sympt_rub-eyes-lamp` | Older man rubbing his eyes under a lamp, newspaper on his lap | `elderly man rubbing tired eyes` |
| `sympt_amsler-grid` | Amsler grid taped to a fridge, hand covering one eye | `amsler grid eye test at home` |
| `sympt_miss-cup` | Hand reaching past a coffee cup and just missing it | `depth perception reaching for cup elderly` |
| `sympt_phone-too-close` | Older person holding a phone inches from their face | `elderly person holding phone close to face` |

## 3. Clinic and proof — the beat that wins

Any line about a specialist, a scan, an appointment, leaking or progression gets a real clinic
shot. The reference control put its entire testimonial over one 7.9 s stock clip of a young
woman drinking water. This block is where we beat it.

| Filename slug | What we need | Search keyword |
|---|---|---|
| `test_creator-talking` | 60+ woman talking to camera, kitchen, phone height — cut into 2–3 s pieces | FILMED CREATOR / real UGC |
| `test_slit-lamp` | Chin on the slit lamp, blue light across the eye | `eye exam slit lamp ophthalmologist` |
| `test_oct-scan-machine` | OCT machine running, retinal scan appearing on the monitor | `OCT retinal scan machine` |
| `test_doctor-points-scan` | Doctor pointing at a scan on screen, patient beside them | `doctor explaining eye scan to patient` |
| `test_doctor-surprised` | Doctor leaning back, surprised, talking to a patient | `doctor surprised talking to patient` |
| `test_dilating-drops` | Dilating drops going into an eye, head tipped back | `dilating eye drops exam` |
| `test_waiting-room` | Eye clinic waiting room, older patients seated | `eye clinic waiting room` |
| `test_appointment-card` | Appointment card or calendar with a clinic date circled | `appointment reminder card calendar close up` |
| `test_injection-tray` | Anti-VEGF injection tray being prepared — the fear. Use SHORT | `intravitreal injection preparation` |
| `test_woman-laughing` | Older woman's face lighting up, small real laugh | `happy senior woman laughing candid` |
| `test_vivid-flowers` | Vivid colour close-up, flowers or paint swatches in hand | `colorful flowers close up vivid` |
| `test_crayon-drawing` | Grandchild's crayon drawing held up, bright colours | `child crayon drawing held up` |
| `test_window-clear-view` | Clear view out a sunlit window, curtain moving | `sunlight through window curtain morning` |

## 4. Ingredients — where the 70 % is actually won

The ingredient block is the longest stretch of these scripts and the easiest place to blow the
AI budget on molecule renders. Every raw material has a real version. Use it.

| Filename slug | What we need | Search keyword |
|---|---|---|
| `ingr_facts-panel-macro` | Macro of the supplement facts panel, finger tracing the list | CLIENT PACKSHOT |
| `ingr_pharmacy-aisle` | Pharmacy vitamin aisle, hand turning a rival bottle to read the back | `pharmacy vitamin aisle shelf` |
| `ingr_marigold` | Marigold field, close on the orange petals (lutein, zeaxanthin) | `marigold flower field close up` |
| `ingr_bilberry` | Hand picking wild bilberries off the bush | `wild bilberry picking close up` |
| `ingr_ginkgo` | Backlit ginkgo leaves on the branch | `ginkgo biloba leaves close up` |
| `ingr_saffron` | Saffron threads weighed or dropped into a dish | `saffron threads macro` |
| `ingr_salmon` | Raw salmon fillet macro (astaxanthin source) | `salmon fillet macro close up` |
| `ingr_lab-pipette` | Gloved hands, pipette into a vial, lab bench | `laboratory pipette vial close up` |
| `ingr_pills-pouring` | Capsules tipping out of a bottle onto white | `pills pouring out of bottle slow motion` |
| `ingr_capsules-palm` | Two capsules shaken into an open palm | `supplement capsules in palm close up` |
| `ingr_capsules-breakfast` | Two capsules in a palm over a breakfast plate, window light | `taking vitamins with breakfast close up` |
| `ingr_water-pour` | Glass of water filling beside the bottle, morning light | `glass of water pouring morning counter` |

## 5. AI whitelist

Seven shots, ~20 s, all inside the eye or the bloodstream where a camera cannot go.
No AI people. No AI product. No AI symptom sims. No molecule renders standing in for a
raw ingredient that exists in the world.

```
A1_ai_blood-retinal-barrier
A2_ai_macular-pigment-rebuild
A3_ai_macula-cross-section
A4_ai_leaking-vessel-stops
A5_ai_astaxanthin-photoreceptor
A6_ai_capsule-retinal-tissue
A7_ai_healthy-vs-degraded-retina
```

## 6. CTA

| Filename slug | What we need | Search keyword |
|---|---|---|
| `cta_three-bottles-pick` | Three bottles lined up, hand picking one | CLIENT PACKSHOT |
| `cta_add-to-cart` | Thumb tapping add to cart | `add to cart phone screen close up` |
| `cta_windowsill-push` | Bottle on a kitchen windowsill, morning light, slow push in | CLIENT PACKSHOT |
| `cta_porch-delivery` | Porch delivery box being picked up | `porch package delivery close up` |
