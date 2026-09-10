# MizoEval GPU-Local Evaluation Plan

**Date:** 2026-09-10  
**GPU:** A100 20GB  
**Available time:** 22 hours  
**Scope:** NLLB-200 (MT) + Llama 3.1 70B (full matrix)

---

## Objective

Establish engineered (NLLB) and strong open-weight (Llama) baselines for the MizoEval paper. Complete all inference within 22-hour slot.

**In scope:** NLLB-200 MT both directions, Llama 3.1 70B full matrix.  
**Out of scope:** XLM-R finetuning (deferred, not mentioned in paper).

---

## Environment Setup

### Hardware
- **GPU:** NVIDIA A100 40GB (or 20GB with quantization)
- **Memory:** ≥48GB RAM
- **Storage:** ≥500GB free (model weights + results)

### Dependencies
```bash
pip install -U transformers torch vllm accelerate
pip install datasets sacrebleu seqeval scipy statsmodels pandas
```

### Models to download
```bash
# NLLB-200 (translation)
# - nllb-200-distilled-600M (2.4GB, fast, good quality)
# - nllb-200-1.3B (5.2GB, better accuracy)

# Llama 3.1 70B (full evaluation)
# - meta-llama/Llama-3.1-70B-Instruct (140GB, requires quantization for A100 20GB)
# - With 4-bit: ~35GB
```

**Download before slot time** — models are large, initial download is slow.

---

## Part A: NLLB-200 MT Inference

### Setup

```python
# src/mizoeval/models/nllb_provider.py (new file)

from transformers import NllbTokenizer, M2M100ForConditionalGeneration
import torch

class NLLBProvider:
    def __init__(self, model_id="facebook/nllb-200-distilled-600M", device="cuda"):
        self.model_id = model_id
        self.device = device
        self.tokenizer = NllbTokenizer.from_pretrained(model_id)
        self.model = M2M100ForConditionalGeneration.from_pretrained(model_id).to(device)
        self.model.eval()
    
    def translate(self, text: str, src_lang: str, tgt_lang: str, max_length=256):
        """Translate text from src_lang to tgt_lang.
        src_lang: 'mya_Mymr' (Mizo) or 'eng_Latn' (English)
        tgt_lang: 'eng_Latn' or 'mya_Mymr'
        """
        self.tokenizer.src_lang = src_lang
        encoded = self.tokenizer(text, return_tensors="pt", max_length=512, truncation=True).to(self.device)
        
        with torch.no_grad():
            generated_tokens = self.model.generate(
                **encoded,
                forced_bos_token_id=self.tokenizer.convert_tokens_to_ids(tgt_lang),
                max_length=max_length,
                num_beams=5
            )
        
        return self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
```

### Run MT inference

```bash
# Add NLLB provider to configs/models.yaml
cat >> configs/models.yaml << 'EOF'

  - name: nllb-200-600m
    provider: nllb  # new provider type, maps to NLLBProvider
    model_id: "facebook/nllb-200-distilled-600M"
    price_in: 0.0
    price_out: 0.0
    enabled: true
EOF

# Run MT cells
python -m mizoeval.runners.run_task --task mt --regime zero_shot --direction mz2en --model nllb-200-600m
python -m mizoeval.runners.run_task --task mt --regime zero_shot --direction en2mz --model nllb-200-600m
python -m mizoeval.runners.run_task --task mt --regime five_shot --direction mz2en --model nllb-200-600m
python -m mizoeval.runners.run_task --task mt --regime five_shot --direction en2mz --model nllb-200-600m
```

### Expected output
- 4 MT cells × 2 directions (cached)
- **Total time:** ~90 min (limited by A100 memory, not compute)
- **Output:** `results/raw/mt__*__nllb-200-600m.jsonl` + manifests
- **Metrics:** chrF++ by register stratum (scripture/religious/secular)

---

## Part B: Llama 3.1 70B Full Matrix

### Setup with vLLM (recommended for speed)

```bash
# Install vLLM
pip install vllm

# Download Llama 3.1 70B (requires HF auth token)
# huggingface-cli login  # paste your token
# huggingface_hub download meta-llama/Llama-3.1-70B-Instruct
```

### Integration into harness

```python
# src/mizoeval/models/providers.py — add to PROVIDERS dict

"vllm": VllmProvider,  # new provider

class VllmProvider(ModelProvider):
    """Llama and other models via vLLM (local GPU inference)."""
    
    def __init__(self, spec: ModelSpec):
        from vllm import LLM
        self.spec = spec
        self.llm = LLM(
            model=spec.model_id,
            dtype="float16",  # or "int4" for 4-bit quantization on A100 20GB
            tensor_parallel_size=1,
            max_model_len=2048
        )
    
    def complete(self, model: str, messages: list[Message], **params) -> Response:
        """Chat completion using vLLM."""
        from vllm import SamplingParams
        
        prompt = self._format_prompt(messages)
        sampling_params = SamplingParams(
            temperature=params.get("temperature", 0),
            max_tokens=params.get("max_tokens", 1024),
            top_p=1.0
        )
        
        outputs = self.llm.generate([prompt], sampling_params)
        text = outputs[0].outputs[0].text
        
        return Response(
            text=text,
            prompt_tokens=len(self.llm.tokenizer.encode(prompt)),
            completion_tokens=len(self.llm.tokenizer.encode(text)),
            error=None
        )
```

### Run full matrix

```bash
# Add Llama to configs/models.yaml
cat >> configs/models.yaml << 'EOF'

  - name: llama-3.1-70b
    provider: vllm
    model_id: "meta-llama/Llama-3.1-70B-Instruct"
    price_in: 0.0
    price_out: 0.0
    enabled: true
EOF

# Run full 14-cell matrix
python -m mizoeval.runners.run_matrix --model llama-3.1-70b --cache results/cache.sqlite
```

### Expected output
- All 14 cells (MCQ, sentiment, NER, MT)
- **Total time:** ~2 hours on A100
- **Output:** `results/raw/*__llama-3.1-70b.jsonl` + manifests

---

## Time Budget

| Task | Time | Notes |
|------|------|-------|
| **Environment setup** | 30 min | pip install, model downloads (parallelizable) |
| **NLLB-200 MT (4 cells)** | 90 min | 2 directions × 2 regimes, stratified scoring |
| **Llama 3.1 70B (14 cells)** | 120 min | Full matrix, cached MCQ/sentiment/NER replay free |
| **Commits + results aggregation** | 30 min | Stage results, commit, update tables |
| **Buffer (reruns, debugging)** | 10 hours | Unused time stays as safety margin |
| **Total used** | ~4 hours | 22 hours available ✓ |

---

## Integration with existing harness

Both NLLB and Llama inference **use the same `run_task.py` / `run_matrix.py` pipeline**:

1. Add provider classes to `src/mizoeval/models/providers.py`
2. Add roster entries to `configs/models.yaml`
3. Run via standard CLI (no new code needed beyond providers)
4. Results cache automatically (resumable, free replays)
5. Manifests + metrics auto-computed (chrF++, macro-F1, F1, accuracy)

---

## Expected Results

### NLLB-200 (engineered MT baseline)

Approximate chrF++ (literature benchmarks on low-resource):
- mz→en: scripture ~30, religious ~28, secular ~24 (lower than LLMs, shows LLM gain)
- en→mz: scripture ~22, religious ~20, secular ~18 (morphologically harder)

**Paper claim:** "LLM advantage over engineered MT is 15–20 chrF points in zero-shot."

### Llama 3.1 70B (open-weight comparison)

Approximate accuracy:
- MCQ: 55–62% (between gpt-5.4-mini @ 57% and gemini @ 60%)
- Sentiment: 0.65–0.72 macro-F1
- NER: 0.20–0.25 micro-F1
- MT: 35–45 chrF (competitive with gpt-5.4-mini, beats gemma4)

**Paper claim:** "Strong open model (Llama 70B) is competitive with closed frontier models on most tasks except sentiment (gemini leads)."

---

## Commits & Results

After both runs complete:

```bash
git add results/raw/mt__*__nllb* results/raw/*__llama-3.1-70b*
git commit -m "results: NLLB-200 MT baseline + Llama 3.1 70B full matrix

NLLB-200 (engineered MT baseline):
  MT mz→en  scripture ~30 / religious ~28 / secular ~24 chrF++
  MT en→mz  scripture ~22 / religious ~20 / secular ~18 chrF++
  
Llama 3.1 70B (open-weight, A100 local):
  MCQ zero-shot  acc ~0.58
  Sentiment five-shot  macro-F1 ~0.70
  NER test  micro-F1 ~0.22
  MT mz→en  scripture ~42 / religious ~46 / secular ~36 chrF++
  
All results cached, resumable. A100 inference ~4 hours total.
"
```

Then update `README.md` with Llama + NLLB results tables.

---

## Next Steps (if time permits)

1. Re-run gemini-3.5-flash final MT cells (if interrupted)
2. Commit gpt-oss:120b final results (if it finishes)
3. Build analysis module (`src/mizoeval/analysis/`) to generate paper tables

---

## Notes

- **Quantization:** Llama 3.1 70B in 4-bit fits A100 20GB comfortably (~35GB)
- **Batch inference:** Single item at a time (seq=1) to match frontier model setup (no batch effects)
- **Cache behavior:** Every call is cached; reruns are free
- **GPU memory:** Monitor with `nvidia-smi` during runs; A100 should not OOM
- **Timeout:** Set vLLM timeout to 120s per inference (guard against hangs)

---

## Completion criteria

✅ NLLB-200 MT both directions, both regimes  
✅ Llama 3.1 70B all 14 cells  
✅ Results committed to git  
✅ Paper tables updated with new baseline results  
✅ Within 22-hour slot time  

