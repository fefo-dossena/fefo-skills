// Visão do Mac (framework Vision) para as checagens do núcleo: rostos, texto (OCR) e mãos em cada imagem.
// Compilado sob demanda por visao.py em ~/.cache/fluxo/visao. Sem dependência de Python.
//   visao <img> [<img> ...]   -> uma linha JSON por imagem:
//   {"arquivo":..., "rostos":[[x,y,w,h]...], "textos":[{"t":..,"c":..,"b":[x,y,w,h]}...], "maos":N}
// Caixas em fração do quadro, origem no canto de CIMA à esquerda (como o ffmpeg/ASS).
import Foundation
import Vision
import AppKit

func caixa(_ r: CGRect) -> [Double] {
    return [Double(r.origin.x), Double(1 - r.origin.y - r.size.height), Double(r.size.width), Double(r.size.height)].map { ($0 * 10000).rounded() / 10000 }
}

for arq in CommandLine.arguments.dropFirst() {
    var saida: [String: Any] = ["arquivo": arq]
    guard let img = NSImage(contentsOfFile: arq),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        saida["erro"] = "não abri"
        if let d = try? JSONSerialization.data(withJSONObject: saida), let s = String(data: d, encoding: .utf8) { print(s) }
        continue
    }
    let rostos = VNDetectFaceRectanglesRequest()
    let texto = VNRecognizeTextRequest()
    texto.recognitionLevel = .accurate
    texto.usesLanguageCorrection = false      // sem correção: o texto deformado da IA tem de aparecer como está
    texto.recognitionLanguages = ["en-US"]
    let maos = VNDetectHumanHandPoseRequest()
    maos.maximumHandCount = 4
    let h = VNImageRequestHandler(cgImage: cg, options: [:])
    try? h.perform([rostos, texto, maos])
    saida["rostos"] = (rostos.results ?? []).map { caixa($0.boundingBox) }
    saida["textos"] = (texto.results ?? []).compactMap { o -> [String: Any]? in
        guard let c = o.topCandidates(1).first else { return nil }
        return ["t": c.string, "c": (Double(c.confidence) * 100).rounded() / 100, "b": caixa(o.boundingBox)]
    }
    saida["maos"] = (maos.results ?? []).count
    if let d = try? JSONSerialization.data(withJSONObject: saida), let s = String(data: d, encoding: .utf8) { print(s) }
}
