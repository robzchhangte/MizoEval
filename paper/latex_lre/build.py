import re, pathlib
src = pathlib.Path('latex/main.tex').read_text(encoding='utf-8').splitlines()
# body: from "\section{Introduction}" to just before "\section*{Data Availability Statement}"
i0 = next(i for i,l in enumerate(src) if l.startswith(r'\section{Introduction}'))
i1 = next(i for i,l in enumerate(src) if l.startswith(r'\section*{Data Availability'))
body = '\n'.join(src[i0:i1]).rstrip()
a0 = next(i for i,l in enumerate(src) if l.startswith(r'\section{Model Version Identifiers}'))
a1 = next(i for i,l in enumerate(src) if l.startswith(r'\end{document}'))
app = '\n'.join(src[a0:a1]).rstrip()
abs_start = next(i for i,l in enumerate(src) if l.startswith(r'\begin{abstract}'))
abs_end = next(i for i,l in enumerate(src) if l.startswith(r'\end{abstract}'))
abstract = ' '.join(l for l in src[abs_start+1:abs_end] if l.strip())

head = r'''% MizoEval -- manuscript for Language Resources and Evaluation (Springer)
% Built from paper/draft.md with the Springer Nature LaTeX template
% (sn-jnl.cls, author-year style sn-mathphys-ay). The journal uses
% single-blind review, so author details appear in the title block.
% Body text is generated from paper/latex/main.tex by build.py; edit
% that file or draft.md, then rerun build.py.

\documentclass[pdflatex,sn-mathphys-ay]{sn-jnl}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{url}

\begin{document}

\title[MizoEval]{MizoEval: A Multi Task Benchmark for Mizo with a Contamination Aware Machine Translation Protocol}

\author*[1]{\fnm{Robert} \sur{Lalramhluna}}\email{dt21cs003@nitmz.ac.in}

\author[1]{\fnm{Sandeep Kumar} \sur{Dash}}\email{sandeep.cse@nitmz.ac.in}

\author[2]{\fnm{Partha} \sur{Pakray}}\email{partha@cse.nits.ac.in}

\affil*[1]{\orgdiv{Department of Computer Science and Engineering}, \orgname{National Institute of Technology Mizoram}, \orgaddress{\city{Aizawl}, \postcode{796012}, \state{Mizoram}, \country{India}}}

\affil[2]{\orgdiv{Department of Computer Science and Engineering}, \orgname{National Institute of Technology Silchar}, \orgaddress{\city{Silchar}, \postcode{788010}, \state{Assam}, \country{India}}}

\abstract{''' + abstract + r'''}

\keywords{Mizo, low resource languages, large language model evaluation, benchmark, machine translation, data contamination}

\maketitle

'''

tail = r'''

\backmatter

\section*{Declarations}

\bmhead{Funding}
This research received no external funding.

\bmhead{Conflict of interest}
The authors declare no competing interests.

\bmhead{Ethics approval and consent to participate}
This study uses existing, previously collected text data; no new human subjects data was collected for the results reported in this paper.

\bmhead{Consent for publication}
Not applicable.

\bmhead{Data availability}
All four MizoEval task datasets will be made publicly available on Hugging Face at \url{https://huggingface.co/datasets/robzchhangte/MizoEval}, and the accompanying data repair and evaluation harness on GitHub at \url{https://github.com/robzchhangte/MizoEval}, upon publication. Archived copies of the datasets, the harness, and the full result set reported in this paper are deposited on Zenodo at \url{https://doi.org/10.5281/zenodo.23022114}, released on publication.

\bmhead{Author contributions}
Following the CRediT taxonomy: Robert Lalramhluna contributed conceptualization, data curation, formal analysis, investigation, methodology, software, and the original draft. Sandeep Kumar Dash contributed supervision and writing review and editing. Partha Pakray contributed supervision and writing review and editing.

\bmhead{AI usage disclosure}
Claude (Anthropic) assisted with code generation for the experiments and with paraphrasing, editing, and grammar correction of the manuscript text. All code and text were reviewed and verified by the authors, who take full responsibility for the paper's content.

\begin{appendices}

''' + app + r'''

\end{appendices}

\bibliography{references}

\end{document}
'''
pathlib.Path('latex_lre/main.tex').write_text(head + body + tail, encoding='utf-8')
print('ok', len(body), len(app))
