import React, { useState, useCallback, useEffect, useRef } from 'react'

/* ─── i18n ─── */
const T = {
  en: {
    title: 'LangChain Pipeline',
    subtitle: 'Event-Driven Microservices + MLOps',
    tabs: { arch: 'Architecture', pipeline: 'Analysis Pipeline', events: 'Event Log', mlops: 'MLOps Dashboard' },
    selectDoc: 'Select a document to analyze',
    analyze: 'Run Analysis',
    analyzing: 'Analyzing...',
    quick: 'Quick',
    full: 'Full Pipeline',
    results: 'Results',
    summary: 'Summary',
    topics: 'Key Topics',
    sentiment: 'Sentiment',
    risk: 'Risk Level',
    actions: 'Action Items',
    keywords: 'Keywords',
    riskTerms: 'Risk Terms',
    structure: 'Structure',
    qualityScore: 'Quality Score',
    promptName: 'Prompt Name',
    version: 'Version',
    status: 'Status',
    active: 'Active',
    inactive: 'Inactive',
    metric: 'Metric',
    count: 'Count',
    mean: 'Mean',
    min: 'Min',
    max: 'Max',
    noEvents: 'No events yet. Run an analysis to generate events.',
    noMetrics: 'No metrics yet. Run a full analysis to generate metrics.',
    services: { doc: 'Document Service', analysis: 'Analysis Service', report: 'Report Service', bus: 'Event Bus', mlops: 'MLOps Layer', gateway: 'API Gateway' },
    archDesc: 'Three microservices communicate through an in-memory event bus. The API Gateway unifies all endpoints. MLOps layer tracks prompts, metrics, and logs.',
    chainSteps: ['1. Document Ingestion', '2. Tool Analysis (Keywords, Risk, Sentiment)', '3. LangChain Extract Chain', '4. Quality Review Chain', '5. Report Generation'],
    demo: 'Demo Mode',
    voice: 'Voice Assistant',
  },
  es: {
    title: 'LangChain Pipeline',
    subtitle: 'Microservicios Event-Driven + MLOps',
    tabs: { arch: 'Arquitectura', pipeline: 'Pipeline de Analisis', events: 'Log de Eventos', mlops: 'Dashboard MLOps' },
    selectDoc: 'Selecciona un documento para analizar',
    analyze: 'Ejecutar Analisis',
    analyzing: 'Analizando...',
    quick: 'Rapido',
    full: 'Pipeline Completo',
    results: 'Resultados',
    summary: 'Resumen',
    topics: 'Temas Clave',
    sentiment: 'Sentimiento',
    risk: 'Nivel de Riesgo',
    actions: 'Acciones Recomendadas',
    keywords: 'Palabras Clave',
    riskTerms: 'Terminos de Riesgo',
    structure: 'Estructura',
    qualityScore: 'Puntuacion de Calidad',
    promptName: 'Nombre del Prompt',
    version: 'Version',
    status: 'Estado',
    active: 'Activo',
    inactive: 'Inactivo',
    metric: 'Metrica',
    count: 'Cantidad',
    mean: 'Media',
    min: 'Min',
    max: 'Max',
    noEvents: 'Sin eventos aun. Ejecuta un analisis para generar eventos.',
    noMetrics: 'Sin metricas aun. Ejecuta un analisis completo para generar metricas.',
    services: { doc: 'Servicio de Documentos', analysis: 'Servicio de Analisis', report: 'Servicio de Reportes', bus: 'Event Bus', mlops: 'Capa MLOps', gateway: 'API Gateway' },
    archDesc: 'Tres microservicios se comunican a traves de un event bus en memoria. El API Gateway unifica todos los endpoints. La capa MLOps rastrea prompts, metricas y logs.',
    chainSteps: ['1. Ingestion de Documento', '2. Analisis con Tools (Keywords, Riesgo, Sentimiento)', '3. LangChain Extract Chain', '4. Quality Review Chain', '5. Generacion de Reporte'],
    demo: 'Modo Demo',
    voice: 'Asistente de Voz',
  }
}

/* ─── Sample Documents ─── */
const SAMPLES = [
  {
    id: 'contract',
    title: 'Service Agreement',
    titleEs: 'Acuerdo de Servicios',
    type: 'contract',
    content: `PROFESSIONAL SERVICES AGREEMENT\nThis Agreement includes provisions for liability, indemnification, and breach penalties. Provider shall comply with all applicable compliance requirements and maintain confidentiality of proprietary information. Termination may occur with 30 days notice. The total fee is $450,000 payable in monthly installments. Late payments incur a penalty of 1.5% per month. Audit rights are reserved by the Client. Default provisions require 15 business days to cure. Provider's liability shall not exceed total fees paid.`
  },
  {
    id: 'financial',
    title: 'Q4 Financial Report',
    titleEs: 'Reporte Financiero Q4',
    type: 'financial',
    content: `QUARTERLY FINANCIAL REPORT Q4 2024\nRevenue reached $128.5 million, representing a 23% year-over-year increase. Cloud services grew 31% to $72.3M driven by enterprise migration. Net income was $24.6M with strong margins. MRR reached $24.1M up 28% YoY. Customer acquisition cost decreased 15%. Net revenue retention at 118%. Total assets of $412M with $89.2M cash. Debt-to-equity ratio is a healthy 0.18. FY2025 guidance projects 28-35% revenue growth with improved operating margins of 27-29%.`
  },
  {
    id: 'compliance',
    title: 'GDPR Compliance Assessment',
    titleEs: 'Evaluacion de Cumplimiento GDPR',
    type: 'compliance',
    content: `DATA PRIVACY COMPLIANCE ASSESSMENT\nThe organization processes personal data of 2.4 million EU residents and 1.8 million California residents under GDPR and CCPA. Overall compliance score is 78/100. Data processing activities are documented. Encryption uses AES-256 at rest and TLS 1.3 in transit. Gaps identified in consent management, vendor security assessments, and automated decision-making opt-out. GDPR penalties can reach 4% of annual turnover. Remediation deadline is 90 days for critical items. Quarterly audit schedule must be maintained.`
  }
]

/* ─── Demo analysis engine (client-side) ─── */
function demoAnalyze(content, mode) {
  const words = content.split(/\s+/)
  const wordCount = words.length
  const stop = new Set(['the','a','an','is','are','was','were','this','that','and','or','for','to','of','in','on','with','by','at','from','as','it','be','has','have','had','not','but','all','can','its','will','would','may'])
  const wl = content.toLowerCase()
  const filtered = words.map(w => w.toLowerCase().replace(/[^a-z]/g,'')).filter(w => w.length > 3 && !stop.has(w))
  const freq = {}; filtered.forEach(w => { freq[w] = (freq[w]||0)+1 })
  const keywords = Object.entries(freq).sort((a,b)=>b[1]-a[1]).slice(0,10).map(([k,c])=>({keyword:k,count:c}))

  const riskPatterns = {liability:'Legal liability language',breach:'Contract breach terminology',penalty:'Penalty clauses',termination:'Termination provisions',indemnif:'Indemnification clauses',confidential:'Confidentiality requirements',compliance:'Compliance requirements',audit:'Audit provisions',default:'Default conditions',deadline:'Time-sensitive deadlines'}
  const riskTerms = Object.entries(riskPatterns).filter(([p])=>wl.includes(p)).map(([t,f])=>({term:t,flag:f}))

  const posWords = new Set(['good','great','excellent','positive','success','benefit','improve','growth','profit','strong','favorable','increase','healthy'])
  const negWords = new Set(['bad','poor','negative','risk','loss','damage','fail','decline','problem','issue','concern','liability','penalty','breach','gap'])
  const wordSet = new Set(wl.split(/\s+/))
  const pCount = [...wordSet].filter(w=>posWords.has(w)).length
  const nCount = [...wordSet].filter(w=>negWords.has(w)).length
  const sentiment = pCount > nCount ? 'positive' : nCount > pCount ? 'negative' : 'neutral'
  const riskLevel = riskTerms.length > 4 ? 'high' : riskTerms.length > 1 ? 'medium' : 'low'

  const paragraphs = content.split(/\n\n/).filter(p=>p.trim()).length
  const sentences = content.split(/[.!?]+/).filter(s=>s.trim()).length

  const tools = { keywords: JSON.stringify(keywords), risk_terms: riskTerms.length ? JSON.stringify(riskTerms) : 'No risk terms detected', sentiment, structure: JSON.stringify({paragraphs, sentences, words: wordCount}) }

  if (mode === 'quick') {
    const sents = content.split(/[.!?]+/).filter(s=>s.trim().length>20).slice(0,3)
    return { document_id:'demo', summary: sents.join('. ')+'.' || 'Document analyzed successfully.', tools, mode:'quick' }
  }

  const analysis = {
    summary: `Document contains ${wordCount} words. ${riskTerms.length > 0 ? 'Risk factors detected.' : 'No significant risks found.'} Overall tone is ${sentiment}.`,
    key_topics: keywords.slice(0,5).map(k=>k.keyword),
    sentiment, risk_level: riskLevel,
    action_items: ['Review document for compliance requirements','Schedule follow-up review in 30 days','Share findings with stakeholders']
  }
  const quality = { score: 7 + Math.floor(Math.random()*3), improvements: ['Add more specific metrics','Include timeline estimates'] }
  const report = { title:'Document Analysis Report', executive_summary: analysis.summary, findings:['Document structure analyzed','Key terms identified','Risk assessment completed'], recommendations:['Review flagged items','Implement improvements','Schedule re-analysis'], risk_assessment: riskLevel === 'high' ? 'High risk - immediate review recommended' : 'Moderate - standard provisions' }

  return { document_id:'demo', analysis, quality_review: quality, report: JSON.stringify(report), tools, mode:'full' }
}

/* ─── Styles ─── */
const colors = { bg:'#0F172A', surface:'#1E293B', surfaceLight:'#334155', blue:'#3B82F6', green:'#10B981', amber:'#F59E0B', red:'#EF4444', text:'#F8FAFC', textMuted:'#94A3B8', border:'#475569' }

const css = `
*{margin:0;padding:0;box-sizing:border-box}
body{background:${colors.bg};color:${colors.text};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh}
.container{max-width:1200px;margin:0 auto;padding:20px}
.header{display:flex;justify-content:space-between;align-items:center;padding:24px 0;border-bottom:1px solid ${colors.border};margin-bottom:24px;flex-wrap:wrap;gap:12px}
.header h1{font-size:28px;background:linear-gradient(135deg,${colors.blue},${colors.green});-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header p{color:${colors.textMuted};font-size:14px}
.controls{display:flex;gap:8px;align-items:center}
.badge{background:${colors.green}22;color:${colors.green};padding:4px 12px;border-radius:12px;font-size:12px;font-weight:600}
.lang-toggle{background:${colors.surface};border:1px solid ${colors.border};color:${colors.text};padding:6px 12px;border-radius:6px;cursor:pointer;font-size:13px}
.lang-toggle:hover{border-color:${colors.blue}}
.tabs{display:flex;gap:4px;background:${colors.surface};padding:4px;border-radius:10px;margin-bottom:24px;overflow-x:auto}
.tab{padding:10px 20px;border-radius:8px;border:none;background:transparent;color:${colors.textMuted};cursor:pointer;font-size:14px;font-weight:500;white-space:nowrap;transition:all .2s}
.tab:hover{color:${colors.text}}
.tab.active{background:${colors.blue};color:white}
.card{background:${colors.surface};border:1px solid ${colors.border};border-radius:12px;padding:20px;margin-bottom:16px}
.card h3{font-size:16px;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
@media(max-width:768px){.grid2,.grid3{grid-template-columns:1fr}}
.doc-card{background:${colors.surfaceLight};border:2px solid transparent;border-radius:10px;padding:16px;cursor:pointer;transition:all .2s}
.doc-card:hover{border-color:${colors.blue}55}
.doc-card.selected{border-color:${colors.blue}}
.doc-card h4{font-size:15px;margin-bottom:4px}
.doc-card p{color:${colors.textMuted};font-size:13px}
.doc-type{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;text-transform:uppercase}
.type-contract{background:${colors.amber}22;color:${colors.amber}}
.type-financial{background:${colors.green}22;color:${colors.green}}
.type-compliance{background:${colors.blue}22;color:${colors.blue}}
.btn{padding:10px 24px;border-radius:8px;border:none;font-weight:600;cursor:pointer;font-size:14px;transition:all .2s}
.btn-primary{background:${colors.blue};color:white}
.btn-primary:hover{background:#2563EB}
.btn-primary:disabled{opacity:.5;cursor:not-allowed}
.btn-sm{padding:6px 14px;font-size:13px}
.mode-toggle{display:flex;gap:4px;background:${colors.surfaceLight};padding:3px;border-radius:6px}
.mode-btn{padding:6px 12px;border:none;border-radius:4px;background:transparent;color:${colors.textMuted};cursor:pointer;font-size:13px}
.mode-btn.active{background:${colors.blue};color:white}
.result-section{margin-top:8px;padding:12px;background:${colors.surfaceLight};border-radius:8px}
.result-section h4{font-size:13px;color:${colors.textMuted};margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px}
.result-section p,.result-section li{font-size:14px;line-height:1.6}
.result-section ul{padding-left:20px}
.tag{display:inline-block;padding:3px 10px;border-radius:4px;font-size:12px;margin:2px;background:${colors.blue}22;color:${colors.blue}}
.sentiment-positive{color:${colors.green}}
.sentiment-negative{color:${colors.red}}
.sentiment-neutral{color:${colors.amber}}
.risk-low{color:${colors.green}}
.risk-medium{color:${colors.amber}}
.risk-high{color:${colors.red}}
.event-item{display:flex;gap:12px;padding:10px;border-bottom:1px solid ${colors.border};font-size:13px;align-items:center}
.event-topic{font-weight:600;color:${colors.blue};min-width:160px}
.event-time{color:${colors.textMuted};min-width:90px;font-size:12px}
.event-payload{color:${colors.textMuted};flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
table{width:100%;border-collapse:collapse}
th{text-align:left;padding:10px;color:${colors.textMuted};font-size:13px;border-bottom:1px solid ${colors.border}}
td{padding:10px;font-size:14px;border-bottom:1px solid ${colors.border}22}
.arch-diagram{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin:20px 0}
.arch-box{background:${colors.surfaceLight};border:2px solid ${colors.border};border-radius:12px;padding:20px;text-align:center;transition:all .3s}
.arch-box:hover{border-color:${colors.blue};transform:translateY(-2px)}
.arch-box.bus{grid-column:1/-1;background:${colors.blue}11;border-color:${colors.blue}44}
.arch-box.mlops{grid-column:1/-1;background:${colors.green}11;border-color:${colors.green}44}
.arch-box.gw{grid-column:1/-1;background:${colors.amber}11;border-color:${colors.amber}44}
.arch-icon{font-size:32px;margin-bottom:8px}
.arch-label{font-weight:600;font-size:14px}
.arch-desc{color:${colors.textMuted};font-size:12px;margin-top:4px}
.chain-step{display:flex;align-items:center;gap:12px;padding:12px;margin:6px 0;background:${colors.surfaceLight};border-radius:8px;border-left:3px solid ${colors.blue}}
.chain-step.active{border-left-color:${colors.green};background:${colors.green}11}
.chain-step.done{border-left-color:${colors.green};opacity:.7}
.chain-num{width:28px;height:28px;border-radius:50%;background:${colors.blue};color:white;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;flex-shrink:0}
.chain-step.active .chain-num{background:${colors.green}}
.chain-step.done .chain-num{background:${colors.green}}
.voice-btn{position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:50%;background:${colors.blue};border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 20px rgba(59,130,246,.4);transition:all .2s;z-index:100}
.voice-btn:hover{transform:scale(1.1)}
.empty-state{text-align:center;padding:40px;color:${colors.textMuted}}
.score-badge{display:inline-flex;align-items:center;justify-content:center;width:48px;height:48px;border-radius:50%;font-size:18px;font-weight:700}
.score-high{background:${colors.green}22;color:${colors.green}}
.score-mid{background:${colors.amber}22;color:${colors.amber}}
.score-low{background:${colors.red}22;color:${colors.red}}
`

/* ─── App ─── */
export default function App() {
  const [lang, setLang] = useState('en')
  const [tab, setTab] = useState('arch')
  const [selectedDoc, setSelectedDoc] = useState(null)
  const [mode, setMode] = useState('full')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [events, setEvents] = useState([])
  const [metrics, setMetrics] = useState({})
  const [chainStep, setChainStep] = useState(-1)
  const [voiceOpen, setVoiceOpen] = useState(false)
  const t = T[lang]

  const runAnalysis = useCallback(async () => {
    if (!selectedDoc) return
    setLoading(true); setResult(null); setChainStep(0)
    const doc = SAMPLES.find(d => d.id === selectedDoc)

    // Simulate chain steps
    const steps = mode === 'full' ? [0,1,2,3,4] : [0,1]
    for (let i = 0; i < steps.length; i++) {
      setChainStep(steps[i])
      await new Promise(r => setTimeout(r, 400 + Math.random()*300))
    }

    const res = demoAnalyze(doc.content, mode)
    setResult(res)
    setChainStep(-1)
    setLoading(false)

    // Add events
    const now = new Date().toISOString()
    const newEvents = [
      { topic:'document.created', payload:{document_id:doc.id, title:doc.title}, timestamp:now, id:`evt-${Date.now()}` },
      { topic:'analysis.completed', payload:{document_id:doc.id, mode}, timestamp:now, id:`evt-${Date.now()+1}` },
      { topic:'report.generated', payload:{document_id:doc.id}, timestamp:now, id:`evt-${Date.now()+2}` },
    ]
    setEvents(prev => [...newEvents, ...prev].slice(0,50))

    // Add metrics
    if (mode === 'full' && res.quality_review) {
      setMetrics(prev => {
        const aq = prev.analysis_quality || { count:0, total:0 }
        const ac = prev.analyses_completed || { count:0 }
        return {
          ...prev,
          analysis_quality: { count: aq.count+1, total: aq.total + res.quality_review.score, mean: ((aq.total+res.quality_review.score)/(aq.count+1)).toFixed(1), min: Math.min(aq.min||10, res.quality_review.score), max: Math.max(aq.max||0, res.quality_review.score) },
          analyses_completed: { count: ac.count+1 },
        }
      })
    }
  }, [selectedDoc, mode])

  const tryParseJson = (s) => { try { return JSON.parse(s) } catch { return null } }

  return (
    <>
      <style>{css}</style>
      <div className="container">
        {/* Header */}
        <div className="header">
          <div>
            <h1>{t.title}</h1>
            <p>{t.subtitle}</p>
          </div>
          <div className="controls">
            <span className="badge">{t.demo}</span>
            <button className="lang-toggle" onClick={() => setLang(l => l === 'en' ? 'es' : 'en')}>
              {lang === 'en' ? 'ES' : 'EN'}
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="tabs">
          {Object.entries(t.tabs).map(([key, label]) => (
            <button key={key} className={`tab ${tab === key ? 'active' : ''}`} onClick={() => setTab(key)}>{label}</button>
          ))}
        </div>

        {/* Architecture Tab */}
        {tab === 'arch' && (
          <div>
            <div className="card">
              <h3>Microservices Architecture</h3>
              <p style={{color:colors.textMuted,marginBottom:16,fontSize:14}}>{t.archDesc}</p>
              <div className="arch-diagram">
                <div className="arch-box gw">
                  <div className="arch-icon">🌐</div>
                  <div className="arch-label">{t.services.gateway}</div>
                  <div className="arch-desc">FastAPI unified API routing</div>
                </div>
                <div className="arch-box">
                  <div className="arch-icon">📄</div>
                  <div className="arch-label">{t.services.doc}</div>
                  <div className="arch-desc">CRUD + Pydantic validation</div>
                </div>
                <div className="arch-box">
                  <div className="arch-icon">🔬</div>
                  <div className="arch-label">{t.services.analysis}</div>
                  <div className="arch-desc">LangChain + Tools + Bedrock</div>
                </div>
                <div className="arch-box">
                  <div className="arch-icon">📊</div>
                  <div className="arch-label">{t.services.report}</div>
                  <div className="arch-desc">Report generation</div>
                </div>
                <div className="arch-box bus">
                  <div className="arch-icon">⚡</div>
                  <div className="arch-label">{t.services.bus}</div>
                  <div className="arch-desc">In-memory pub/sub (Redis-like pattern)</div>
                </div>
                <div className="arch-box mlops">
                  <div className="arch-icon">📈</div>
                  <div className="arch-label">{t.services.mlops}</div>
                  <div className="arch-desc">Prompt Registry + Metrics Tracker + Structured Logger</div>
                </div>
              </div>
            </div>

            <div className="card">
              <h3>Tech Stack</h3>
              <div className="grid3">
                <div><strong style={{color:colors.blue}}>Backend</strong><p style={{fontSize:13,color:colors.textMuted,marginTop:4}}>FastAPI, LangChain, Pydantic, AWS Bedrock, Python 3.11+</p></div>
                <div><strong style={{color:colors.green}}>Frontend</strong><p style={{fontSize:13,color:colors.textMuted,marginTop:4}}>React 18, Vite, Vercel</p></div>
                <div><strong style={{color:colors.amber}}>MLOps</strong><p style={{fontSize:13,color:colors.textMuted,marginTop:4}}>Versioned Prompts, Quality Metrics, Structured Logging</p></div>
              </div>
            </div>
          </div>
        )}

        {/* Pipeline Tab */}
        {tab === 'pipeline' && (
          <div>
            <div className="card">
              <h3>{t.selectDoc}</h3>
              <div className="grid3">
                {SAMPLES.map(doc => (
                  <div key={doc.id} className={`doc-card ${selectedDoc === doc.id ? 'selected' : ''}`} onClick={() => { setSelectedDoc(doc.id); setResult(null) }}>
                    <span className={`doc-type type-${doc.type}`}>{doc.type}</span>
                    <h4 style={{marginTop:8}}>{lang === 'es' ? doc.titleEs : doc.title}</h4>
                    <p>{doc.content.substring(0, 80)}...</p>
                  </div>
                ))}
              </div>
            </div>

            {selectedDoc && (
              <div className="card">
                <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',flexWrap:'wrap',gap:12}}>
                  <div className="mode-toggle">
                    <button className={`mode-btn ${mode === 'quick' ? 'active' : ''}`} onClick={() => setMode('quick')}>{t.quick}</button>
                    <button className={`mode-btn ${mode === 'full' ? 'active' : ''}`} onClick={() => setMode('full')}>{t.full}</button>
                  </div>
                  <button className="btn btn-primary" onClick={runAnalysis} disabled={loading}>
                    {loading ? t.analyzing : t.analyze}
                  </button>
                </div>

                {/* Chain visualization */}
                {(loading || result) && (
                  <div style={{marginTop:16}}>
                    {t.chainSteps.slice(0, mode === 'full' ? 5 : 2).map((step, i) => (
                      <div key={i} className={`chain-step ${chainStep === i ? 'active' : chainStep > i || result ? 'done' : ''}`}>
                        <div className="chain-num">{i+1}</div>
                        <span style={{fontSize:14}}>{step}</span>
                        {chainStep === i && <span style={{color:colors.amber,fontSize:12,marginLeft:'auto'}}>Processing...</span>}
                        {(chainStep > i || result) && <span style={{color:colors.green,fontSize:12,marginLeft:'auto'}}>Done</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Results */}
            {result && (
              <div className="card">
                <h3>{t.results}</h3>
                {result.mode === 'quick' ? (
                  <div className="result-section">
                    <h4>{t.summary}</h4>
                    <p>{result.summary}</p>
                  </div>
                ) : (
                  <>
                    <div className="grid2">
                      <div className="result-section">
                        <h4>{t.summary}</h4>
                        <p>{result.analysis?.summary}</p>
                      </div>
                      <div className="result-section">
                        <h4>{t.qualityScore}</h4>
                        <div style={{display:'flex',alignItems:'center',gap:12}}>
                          <div className={`score-badge ${result.quality_review?.score >= 8 ? 'score-high' : result.quality_review?.score >= 5 ? 'score-mid' : 'score-low'}`}>
                            {result.quality_review?.score}
                          </div>
                          <span style={{color:colors.textMuted,fontSize:13}}>/10</span>
                        </div>
                      </div>
                    </div>
                    <div className="grid2" style={{marginTop:12}}>
                      <div className="result-section">
                        <h4>{t.topics}</h4>
                        <div>{result.analysis?.key_topics?.map((topic,i) => <span key={i} className="tag">{topic}</span>)}</div>
                      </div>
                      <div className="result-section">
                        <h4>{t.sentiment} / {t.risk}</h4>
                        <p><span className={`sentiment-${result.analysis?.sentiment}`} style={{fontWeight:600}}>{result.analysis?.sentiment}</span> &nbsp;|&nbsp; <span className={`risk-${result.analysis?.risk_level}`} style={{fontWeight:600}}>{result.analysis?.risk_level}</span></p>
                      </div>
                    </div>
                    <div className="result-section" style={{marginTop:12}}>
                      <h4>{t.actions}</h4>
                      <ul>{result.analysis?.action_items?.map((item,i) => <li key={i}>{item}</li>)}</ul>
                    </div>
                  </>
                )}

                {/* Tool results */}
                <div className="grid2" style={{marginTop:12}}>
                  <div className="result-section">
                    <h4>{t.keywords}</h4>
                    <div>{tryParseJson(result.tools?.keywords)?.slice(0,6).map((k,i) => <span key={i} className="tag">{k.keyword} ({k.count})</span>) || result.tools?.keywords}</div>
                  </div>
                  <div className="result-section">
                    <h4>{t.riskTerms}</h4>
                    {(() => {
                      const parsed = tryParseJson(result.tools?.risk_terms)
                      if (parsed && Array.isArray(parsed)) return parsed.map((r,i) => <div key={i} style={{fontSize:13,marginBottom:4}}><strong style={{color:colors.amber}}>{r.term}</strong>: {r.flag}</div>)
                      return <p style={{fontSize:13}}>{result.tools?.risk_terms}</p>
                    })()}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Events Tab */}
        {tab === 'events' && (
          <div className="card">
            <h3>Event Log ({events.length} events)</h3>
            {events.length === 0 ? (
              <div className="empty-state">{t.noEvents}</div>
            ) : (
              events.map((evt, i) => (
                <div key={i} className="event-item">
                  <span className="event-time">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                  <span className="event-topic">{evt.topic}</span>
                  <span className="event-payload">{JSON.stringify(evt.payload)}</span>
                </div>
              ))
            )}
          </div>
        )}

        {/* MLOps Tab */}
        {tab === 'mlops' && (
          <div>
            <div className="card">
              <h3>Prompt Registry</h3>
              <table>
                <thead><tr><th>{t.promptName}</th><th>{t.version}</th><th>{t.status}</th></tr></thead>
                <tbody>
                  <tr><td>extract_analysis</td><td>1.0.0</td><td><span className="badge">{t.active}</span></td></tr>
                  <tr><td>quality_review</td><td>1.0.0</td><td><span className="badge">{t.active}</span></td></tr>
                  <tr><td>quick_summary</td><td>1.0.0</td><td><span className="badge">{t.active}</span></td></tr>
                </tbody>
              </table>
            </div>

            <div className="card">
              <h3>Quality Metrics</h3>
              {Object.keys(metrics).length === 0 ? (
                <div className="empty-state">{t.noMetrics}</div>
              ) : (
                <table>
                  <thead><tr><th>{t.metric}</th><th>{t.count}</th><th>{t.mean}</th><th>{t.min}</th><th>{t.max}</th></tr></thead>
                  <tbody>
                    {Object.entries(metrics).map(([name, m]) => (
                      <tr key={name}>
                        <td style={{fontWeight:600}}>{name}</td>
                        <td>{m.count}</td>
                        <td>{m.mean || '-'}</td>
                        <td>{m.min || '-'}</td>
                        <td>{m.max || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ElevenLabs Voice Button */}
      <button className="voice-btn" onClick={() => setVoiceOpen(v => !v)} title={t.voice}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
        </svg>
      </button>
      {voiceOpen && (
        <div style={{position:'fixed',bottom:90,right:24,width:350,height:400,borderRadius:16,overflow:'hidden',boxShadow:'0 8px 40px rgba(0,0,0,.5)',zIndex:100}}>
          <elevenlabs-convai agent-id="agent_5601kmfx9vnzeb691cj64x2khmm0" style={{width:'100%',height:'100%'}}></elevenlabs-convai>
          <script src="https://elevenlabs.io/convai-widget/index.js" async></script>
        </div>
      )}
    </>
  )
}
