# Axis titles, titles and styles for rivet-mkhtml / rivet-cmphistos. LaTeX syntax.
# Found automatically through RIVET_ANALYSIS_PATH (set in env.sh). Needs no recompilation.
#
# A histogram gets the settings of every block whose regex matches the start of its name (Python
# re.match), later blocks overriding earlier ones. So the title comes from the channel blocks and the
# axis labels from the variable blocks.

# BEGIN PLOT /DYplusJets/.*
LegendXPos=0.60
LegendYPos=0.90
RatioPlotYLabel=EFT/SM
LogY=1
# END PLOT

# Channels
# BEGIN PLOT /DYplusJets/zj_ll_.*
Title=$pp \to \ell\ell$ + $\geq$1 jet
# END PLOT
# BEGIN PLOT /DYplusJets/zj_ee_.*
Title=$pp \to ee$ + $\geq$1 jet
# END PLOT
# BEGIN PLOT /DYplusJets/zj_mm_.*
Title=$pp \to \mu\mu$ + $\geq$1 jet
# END PLOT

# Variables: the dilepton system
# BEGIN PLOT /DYplusJets/.*_mll
XLabel=$m_{\ell\ell}$ [GeV]
YLabel=$\mathrm{d}\sigma/\mathrm{d}m_{\ell\ell}$ [pb/GeV]
LogX=1
# END PLOT
# BEGIN PLOT /DYplusJets/.*_pTll
XLabel=$p_\mathrm{T}^{\ell\ell}$ [GeV]
YLabel=$\mathrm{d}\sigma/\mathrm{d}p_\mathrm{T}^{\ell\ell}$ [pb/GeV]
# END PLOT
# BEGIN PLOT /DYplusJets/.*_yll
XLabel=$y_{\ell\ell}$
YLabel=$\mathrm{d}\sigma/\mathrm{d}y_{\ell\ell}$ [pb]
# END PLOT
# BEGIN PLOT /DYplusJets/.*_etall
XLabel=$\eta_{\ell\ell}$
YLabel=$\mathrm{d}\sigma/\mathrm{d}\eta_{\ell\ell}$ [pb]
# END PLOT
# BEGIN PLOT /DYplusJets/.*_phill
XLabel=$\phi_{\ell\ell}$
YLabel=$\mathrm{d}\sigma/\mathrm{d}\phi_{\ell\ell}$ [pb]
LogY=0
# END PLOT
# BEGIN PLOT /DYplusJets/.*_cosThetaCS
XLabel=$\cos\theta^*_\mathrm{CS}$
YLabel=$\mathrm{d}\sigma/\mathrm{d}\cos\theta^*_\mathrm{CS}$ [pb]
# END PLOT
# The .*_mll block above also matches the slices (patterns match the start of the name): undo its settings
# BEGIN PLOT /DYplusJets/.*_cosThetaCS_mll.*
YLabel=$\mathrm{d}\sigma/\mathrm{d}\cos\theta^*_\mathrm{CS}$ [pb]
LogX=0
# END PLOT
# BEGIN PLOT /DYplusJets/.*_cosThetaCS_mll0
XLabel=$\cos\theta^*_\mathrm{CS}$, $25 < m_{\ell\ell} < 81$ GeV
# END PLOT
# BEGIN PLOT /DYplusJets/.*_cosThetaCS_mll1
XLabel=$\cos\theta^*_\mathrm{CS}$, $81 < m_{\ell\ell} < 101$ GeV
# END PLOT
# BEGIN PLOT /DYplusJets/.*_cosThetaCS_mll2
XLabel=$\cos\theta^*_\mathrm{CS}$, $101 < m_{\ell\ell} < 150$ GeV
# END PLOT
# BEGIN PLOT /DYplusJets/.*_cosThetaCS_mll3
XLabel=$\cos\theta^*_\mathrm{CS}$, $150 < m_{\ell\ell} < 2000$ GeV
# END PLOT
# BEGIN PLOT /DYplusJets/.*_phiStar
XLabel=$\phi^*_\eta$
YLabel=$\mathrm{d}\sigma/\mathrm{d}\phi^*_\eta$ [pb]
# END PLOT

# Variables: the leptons, pT ordered
# BEGIN PLOT /DYplusJets/.*_pTlep1
XLabel=Leading lepton $p_\mathrm{T}$ [GeV]
YLabel=$\mathrm{d}\sigma/\mathrm{d}p_\mathrm{T}^{\ell_1}$ [pb/GeV]
# END PLOT
# BEGIN PLOT /DYplusJets/.*_pTlep2
XLabel=Subleading lepton $p_\mathrm{T}$ [GeV]
YLabel=$\mathrm{d}\sigma/\mathrm{d}p_\mathrm{T}^{\ell_2}$ [pb/GeV]
# END PLOT
# BEGIN PLOT /DYplusJets/.*_etalep1
XLabel=Leading lepton $\eta$
YLabel=$\mathrm{d}\sigma/\mathrm{d}\eta_{\ell_1}$ [pb]
# END PLOT
# BEGIN PLOT /DYplusJets/.*_etalep2
XLabel=Subleading lepton $\eta$
YLabel=$\mathrm{d}\sigma/\mathrm{d}\eta_{\ell_2}$ [pb]
# END PLOT
# BEGIN PLOT /DYplusJets/.*_philep1
XLabel=Leading lepton $\phi$
YLabel=$\mathrm{d}\sigma/\mathrm{d}\phi_{\ell_1}$ [pb]
LogY=0
# END PLOT
# BEGIN PLOT /DYplusJets/.*_philep2
XLabel=Subleading lepton $\phi$
YLabel=$\mathrm{d}\sigma/\mathrm{d}\phi_{\ell_2}$ [pb]
LogY=0
# END PLOT

# Variables: the jets
# BEGIN PLOT /DYplusJets/.*_pTj
XLabel=Leading jet $p_\mathrm{T}$ [GeV]
YLabel=$\mathrm{d}\sigma/\mathrm{d}p_\mathrm{T}^{j}$ [pb/GeV]
LogX=1
# END PLOT
# BEGIN PLOT /DYplusJets/.*_yj
XLabel=$y_{j}$
YLabel=$\mathrm{d}\sigma/\mathrm{d}y_{j}$ [pb]
# END PLOT
# BEGIN PLOT /DYplusJets/.*_etaj
XLabel=Leading jet $\eta$
YLabel=$\mathrm{d}\sigma/\mathrm{d}\eta_{j}$ [pb]
# END PLOT
# BEGIN PLOT /DYplusJets/.*_phij
XLabel=Leading jet $\phi$
YLabel=$\mathrm{d}\sigma/\mathrm{d}\phi_{j}$ [pb]
LogY=0
# END PLOT
# BEGIN PLOT /DYplusJets/.*_HT
XLabel=$H_\mathrm{T}$ [GeV]
YLabel=$\mathrm{d}\sigma/\mathrm{d}H_\mathrm{T}$ [pb/GeV]
# END PLOT

# Variables: the Z + leading jet system
# BEGIN PLOT /DYplusJets/.*_ystarZj
XLabel=$y^* = |y_{\ell\ell} - y_{j}|/2$
YLabel=$\mathrm{d}\sigma/\mathrm{d}y^*$ [pb]
# END PLOT
# BEGIN PLOT /DYplusJets/.*_yboostZj
XLabel=$y_\mathrm{b} = |y_{\ell\ell} + y_{j}|/2$
YLabel=$\mathrm{d}\sigma/\mathrm{d}y_\mathrm{b}$ [pb]
# END PLOT
# BEGIN PLOT /DYplusJets/.*_ybPlusystar
XLabel=$y_\mathrm{b} + y^* = \max(|y_{\ell\ell}|, |y_{j}|)$
YLabel=$\mathrm{d}\sigma/\mathrm{d}(y_\mathrm{b} + y^*)$ [pb]
# END PLOT
# BEGIN PLOT /DYplusJets/.*_dPhiZj
XLabel=$\Delta\phi(\ell\ell, j)$
YLabel=$\mathrm{d}\sigma/\mathrm{d}\Delta\phi(\ell\ell, j)$ [pb]
# END PLOT
# BEGIN PLOT /DYplusJets/.*_zeppenfeld
XLabel=$|y_{\ell\ell} - (y_{j_1} + y_{j_2})/2|$
YLabel=$\mathrm{d}\sigma/\mathrm{d}|y_{\ell\ell} - (y_{j_1} + y_{j_2})/2|$ [pb]
# END PLOT

# Counting histograms
# BEGIN PLOT /DYplusJets/ll_nJets
Title=$pp \to \ell\ell$ + jets
XLabel=Number of jets (last bin: 7 or more)
YLabel=$\sigma$ [pb]
# END PLOT
# BEGIN PLOT /DYplusJets/ll_yields
Title=$pp \to \ell\ell$ + jets
XLabel=Selection (Z = all, Z+j = zj)
YLabel=$\sigma$ [pb]
XCustomMajorTicks=0.5	Z	1.5	Z+j
# END PLOT
