# Pesquisa 4: NiiVue (desenho, reslice oblíquo, window/level) e alternativas

Data da pesquisa: 2026-11-08. Escopo: API de desenho do NiiVue, reslice oblíquo, presets de janela, alternativas (Cornerstone3D, OHIF, Papaya) e ferramentas tipo livewire ou brush por limiar.

**Método:** leitura direta do código-fonte do NiiVue 0.68.1 (CDN jsdelivr), da documentação do wrapper Python (ipyniivue) e da documentação do Cornerstone3D. Os resultados de busca na web foram poucos e pouco específicos. Itens marcados como **[não verificado]** não foram confirmados em código ou documentação nesta pesquisa.

---

## 1. API de desenho do NiiVue (JavaScript)

Confirmado no código-fonte da versão 0.68.1 (`src/niivue/index.ts`):

| Função / propriedade | Situação | Observação |
|---|---|---|
| `opts.drawingEnabled` / `setDrawingEnabled(bool)` | Confirmado | Liga e desliga o modo de desenho. |
| `setPenValue(penValue, isFilledPen = false)` | Confirmado | Valor do pincel (rótulo). `isFilledPen = true` ativa o modo de preenchimento de contorno. |
| `drawPenFilled()` | Confirmado | Preenche o contorno fechado desenhado. |
| `drawUndo()` | Confirmado | Desfaz (pilha em `drawUndoBitmaps`, índice `currentDrawUndoBitmap`). |
| `drawBitmap` (getter/setter, `Uint8Array`) | Confirmado | Acesso ao bitmap do desenho, para enviar ao servidor. |
| `loadDrawing(drawingBitmap: NVImage): boolean` | Confirmado | Carrega um desenho existente como `NVImage`. |
| `saveImage(options): Promise<boolean \| Uint8Array>` | Confirmado a assinatura | Os campos de `SaveImageOptions` (inclusive a opção de salvar o desenho) **[não verificado]**. |
| `closeDrawing()` | **[não verificado]** | Aparece chamado em `handleFilesDrop`, mas a definição não foi encontrada no trecho lido. Existe `close_drawing()` no wrapper Python. |
| Borracha | **[não verificado]** | Não encontrei opção explícita. Convenção a validar no código: valor de pincel 0. |
| Pen type (`opts.penType`) | Propriedade existe | Valores possíveis **[não verificado]**. |

Wrapper Python (ipyniivue, referência de nomes): `set_pen_value(pen_value, is_filled_pen)`, `set_drawing_enabled`, `draw_undo()`, `close_drawing()`, `load_drawing(path)`, `save_image(file_name, is_save_drawing)`, `set_draw_colormap`.

**Versão:** a mais recente encontrada foi a **v0.69.0 (publicada em 20/05/2026)**, via registro Zenodo. Não consegui ver as notas de versão completas. Como a data de hoje é novembro de 2026, pode haver versão mais nova **[não verificado]**. Para o CDN, fixar a versão exata (ex.: `@niivue/niivue@0.69.0`), conforme a regra do projeto.

**Desenhar, salvar e enviar ao servidor:** o fluxo prático é `nv.drawBitmap` (Uint8Array na grade do volume) para o FastAPI, ou `saveImage` com desenho, se as opções forem confirmadas. Para o cálculo de média de HU e área, a máscara deve estar na mesma grade do volume carregado.

**Pontos de atenção:**
- Não encontrei nenhum exemplo oficial de segmentação manual com contorno que use essas funções. O README só cita, como projeto de terceiros, o CACTAS, que "estende o desenho e a segmentação do NiiVue".

## 2. Reslice oblíquo em 2D

**Resposta curta: não encontrei suporte a planos oblíquos no NiiVue.**

- Tipos de fatia confirmados: `SLICE_TYPE` com `AXIAL`, `CORONAL`, `SAGITTAL`, `MULTIPLANAR` e `RENDER`. Método `setSliceType(st)`.
- Rotação de volume 3D no modo `RENDER`: `setRenderAzimuthElevation(a, e)` e `setClipPlane`. Isso gira a visualização 3D, não gera um plano de corte arbitrário em 2D.
- Não encontrei nenhuma opção do tipo `obliqueSlice` no código lido.

**Recomendação: reslice no servidor com SimpleITK.** O NiiVue exibe o NIfTI reamostrado, com a orientação do cabeçalho. A máscara é desenhada na grade reorientada.

Sketch (**não executado**, validar antes de usar):

```python
import numpy as np, SimpleITK as sitk

img = sitk.ReadImage("ombro.nii.gz")
p_prox = np.array([...])   # mm, ponto proximal no eixo do úmero
p_dist = np.array([...])   # mm, ponto distal no eixo do úmero
d = (p_dist - p_prox) / np.linalg.norm(p_dist - p_prox)   # normal do plano axial novo

ref = np.array([...])      # eixo no plano da escápula (a definir)
x = ref - np.dot(ref, d) * d
x /= np.linalg.norm(x)
y = np.cross(d, x)
M = np.column_stack([x, y, d])                 # colunas = eixos
direction = M.ravel().tolist()                 # SimpleITK usa matriz linha-maior

size = np.array(img.GetSize())
sp = np.array(img.GetSpacing())
centro = np.array(img.TransformContinuousIndexToPhysicalPoint([(s-1)/2 for s in img.GetSize()]))
origin = centro - M @ ((size-1)/2 * sp)        # centro do volume novo = centro do original

res = sitk.ResampleImageFilter()
res.SetOutputDirection(direction)
res.SetOutputOrigin(origin.tolist())
res.SetSize(size.tolist())
res.SetOutputSpacing(sp.tolist())
res.SetInterpolator(sitk.sitkLinear)
res.SetDefaultPixelValue(-1024)                # ar em HU
res.SetOutputPixelType(img.GetPixelID())
sitk.WriteImage(res.Execute(img), "ombro_reorientado.nii.gz")
```

**Atenção:**
- A rotação com `Euler3DTransform` e `Resample` (exemplos de fóruns do ITK) é a alternativa. Os fóruns mostram que a grade de saída pode cortar partes do volume; nesse caso, aumentar `SetSize`.
- Ao reorientar, a máscara desenhada fica na grade nova. Para área em mm² e média de HU, há duas opções: (a) calcular as estatísticas no volume reamostrado (a interpolação linear altera levemente os valores de HU); (b) transformar a máscara de volta para a grade original com vizinho mais próximo. A opção (a) é mais simples; a (b) é mais fiel ao dado original.
- O plano de referência do eixo x (escápula) precisa ser definido de forma reprodutível. Isso é decisão de projeto, não de software.

## 3. Presets de janela (window/level) no NiiVue

- Propriedades confirmadas: `volumes[i].cal_min` e `volumes[i].cal_max`. Também existem `robust_min`, `robust_max`, `global_min`, `global_max`.
- Funções confirmadas: `calculateNewRange({volIdx})`, `resetBriCon()`, `windowingHandler(x, y, volIdx)`.
- **Não encontrei `setWindow` na API JavaScript.** No wrapper Python, o `Volume` tem `cal_min`/`cal_max` como traits.
- Na busca, um trecho do código do NVImage indica que `cal_min` e `cal_max` passados no carregamento sobrescrevem os valores do cabeçalho, com `trustCalMinMax = true` por padrão **[verificado só em trecho de busca]**.

Conversão janela → limites (aritmética padrão): `cal_min = L - W/2`, `cal_max = L + W/2`. Exemplo: W=400, L=40 dá `cal_min = -160`, `cal_max = 240`.

Forma sugerida (**não testado**): após o carregamento, `nv.volumes[0].cal_min = ...; nv.volumes[0].cal_max = ...;` e depois atualizar a exibição. O nome exato do método de atualização (`updateGLVolume` ou outro) **[não verificado]**.

Os presets (valores de L e W) devem ser definidos pelo cirurgião. Isso é decisão do usuário.

## 4. Alternativas se o desenho do NiiVue não bastar

| Ferramenta | Prós | Contras (para página única sem build) |
|---|---|---|
| **Cornerstone3D** | Ferramentas de segmentação prontas: `BrushTool`, `RectangleScissorTool`, `CircleScissorTool`, `SphereScissorTool`, `RectangleROIThresholdTool`. A documentação diz que funcionam em todas as vistas (axial, coronal, sagital). Ferramentas de contorno livre e livewire aparecem na API da v1 (`PlanarFreehandROITool`, `LivewireContourTool`). | Usa vtk.js e um sistema de ferramentas próprio. Setup maior que o NiiVue. A documentação de livewire na v3 não foi confirmada. Exige atenção à versão. Reslice oblíquo **[não verificado]**. |
| **OHIF** | Visualizador completo, com Cornerstone3D por baixo. | Aplicação React com build. Não serve para página única sem build. |
| **Papaya** | Leve, sem build. | Projeto com pouca atividade recente. Sem ferramentas de segmentação modernas **[não verificado nesta pesquisa]**. |

Recomendação: manter o NiiVue para visualização e carregamento. Se o desenho manual for insuficiente, considerar Cornerstone3D via ESM do CDN, sem build, mas isso precisa de teste.

## 5. Livewire, intelligent scissors ou brush por limiar

- **Livewire:** não encontrei no NiiVue. No Cornerstone3D há `LivewireContourTool` (API v1) e um exemplo de livewire na v3 **[não verificado na v3]**.
- **Brush por limiar:** o NiiVue tem `doClickToSegment({x, y, tileIndex})` com callback `onClickToSegment({mm3, mL})`, que devolve volume e mL. O comportamento exato (crescimento de região ou limiar) **[não verificado]**. Também há `draw_otsu(levels)` e `draw_grow_cut()` no wrapper Python. Vale testar `doClickToSegment` antes de implementar algo próprio.
- **Interpolação entre fatias:** `interpolateMaskSlices` e `doIntensityGuidedInterpolation` (guiada pela intensidade) existem no código. Podem ajudar caso o contorno seja feito em mais de uma fatia.
- No Cornerstone3D, o `RectangleROIThresholdTool` é a opção de limiar mais direta.

## Não verificado (resumo)

- Nomes exatos de `closeDrawing` e da borracha em JavaScript.
- Campos de `SaveImageOptions` e formato do retorno de `saveImage`.
- Valores de `penType`.
- Versão atual do NiiVue depois de 0.69.0.
- Comportamento real de `doClickToSegment`.
- Método de atualização da exibição após mudar `cal_min`/`cal_max`.
- Código do SimpleITK acima: não executado.
- Suporte a livewire e reslice oblíquo no Cornerstone3D atual.
- Estado de manutenção do Papaya.

## Fontes

- NiiVue 0.68.1, código principal: https://cdn.jsdelivr.net/npm/@niivue/niivue@0.68.1/src/niivue/index.ts
- NiiVue 0.68.1, tipos de desenho: https://cdn.jsdelivr.net/npm/@niivue/niivue@0.68.1/build/drawing/index.d.ts
- NiiVue 0.68.1, pen tool: https://cdn.jsdelivr.net/npm/@niivue/niivue@0.68.1/src/niivue/drawing/PenTool.ts
- Documentação da API do ipyniivue (Python): https://niivue.github.io/ipyniivue/api.html
- JSDoc antigo do niivue.js (2021, referência histórica): https://hanayik.github.io/niivue/api-docs/niivue.js.html
- Repositório NiiVue: https://github.com/niivue/niivue
- Release v0.69.0 (20/05/2026): https://zenodo.org/records/19698061/latest
- Release v0.68.2 (abr/2026): https://zenodo.org/records/19698061
- Cornerstone3D, ferramentas de segmentação: https://cornerstonejs.org/docs/concepts/cornerstone-tools/segmentation/segmentation-tools
- Cornerstone v1, API de ferramentas: https://v1.cornerstonejs.org/api/tools
- ITK Discourse, oblíquo 2D com SimpleITK: https://discourse.itk.org/t/how-to-get-oblique-2d-slice-from-volume-simpleitk/6028
- ITK Discourse, Euler3D e tamanho de saída: https://discourse.itk.org/t/simpleitk-euler3d-transform-problem-with-output-size-resampling/4387
- Notebook oficial SimpleITK, transformações e reamostragem: https://nbviewer.org/github/InsightSoftwareConsortium/SimpleITK-Notebooks/blob/test_pypi_prerelease/Python/21_Transforms_and_Resampling.ipynb
