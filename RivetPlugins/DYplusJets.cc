/*
DYplusJets: Differential cross sections measurement for pp -> Z/gamma*(-> ee, mumu) + jets,
            inclusive in the jets, main c & b jets, no tagging on gen-level; 
            and SMEFT measurement with EFT2Obs.

Rivet routine: EFT2Obs gives every event one weight per reweighting point, and Rivet fills each
                histogram once per weight.
                get_scaling.py then turns those histograms into per-bin SMEFT scaling functions,
                so nothing in this routine is SMEFT-specific.

Observables: y*, y_boost, pT(ll)    with binning are from the CMS Z+jet triple-differential 
                                    measurement, CMS-PAS-SMP-24-010
             rapidity ~ cos theta  

Object cuts: match to our PocketCoffea analysis: https://gitlab.cern.ch/cms-analysis/smp/vjetsrun3
             all cuts are at particle level, with no detector effects.

Histogram names: zj_<channel>_<variable>, e.g. zj_ll_pTll. zj = at least 1 jet.
                 channel: ee, mm, ll (ll = ee + mm)
                 The "jet" in Z-jet variables is the leading jet.
                 ll_nJets has every Z event, including those with no jet.

Storage note: Every histogram costs about (bins x 596 weights) in the output file, so the ee and mm
              channels only get the variables listed in FIT_VARIABLES.
*/

#include "Rivet/Analysis.hh"
#include "Rivet/Projections/FinalState.hh"
#include "Rivet/Projections/FastJets.hh"
#include "Rivet/Projections/VetoedFinalState.hh"
#include "Rivet/Projections/ZFinder.hh"

namespace Rivet {


  class DYplusJets : public Analysis {
  public:
    // Constructor
    RIVET_DEFAULT_ANALYSIS_CTOR(DYplusJets);

    /// Runs once at the start: declare the projections and book the histograms
    void init() {

      // Main selection: Z candidate = opposite-sign, same-flavour pair of prompt dressed leptons in the
      // mass window, done by Zfinder. One ZFinder per flavour.
      //
      // AddPhotons::YES matters twice:
      //  - constituents() returns the dressed leptons, not the bare ones
      //  - the photons used for dressing are removed from the jet input below

      const FinalState fs;
      const Cut lepton_cuts = Cuts::abseta < LEPTON_ABSETA_MAX && Cuts::pT > LEPTON_PT_MIN;
      const ZFinder zee(fs, lepton_cuts, PID::ELECTRON, MLL_MIN, MLL_MAX, DRESSING_DR,
                        ZFinder::ChargedLeptons::PROMPT, ZFinder::ClusterPhotons::NODECAY,
                        ZFinder::AddPhotons::YES);
      const ZFinder zmm(fs, lepton_cuts, PID::MUON, MLL_MIN, MLL_MAX, DRESSING_DR,
                        ZFinder::ChargedLeptons::PROMPT, ZFinder::ClusterPhotons::NODECAY,
                        ZFinder::AddPhotons::YES);
      declare(zee, "Zee");
      declare(zmm, "Zmm");

      // Anti-kT R = 0.4 jets from everything except the Z leptons and their photons.
      // FastJets ignores neutrinos by default.
      VetoedFinalState jet_input(fs);
      jet_input.addVetoOnThisFinalState(zee);
      jet_input.addVetoOnThisFinalState(zmm);
      declare(FastJets(jet_input, FastJets::ANTIKT, JET_R), "Jets");

       // Bin edges per variable. pTll, y*, y_b follow CMS-PAS-SMP-24-010; the rest follow the PocketCoffea analysis.
      const map<string, vector<double>> edges = {
        // Dilepton system -> Z
        // mll: 5 GeV bins around the peak, wider bins in the tail, where the SMEFT/SM ratio grows
        {"mll",           {25, 40, 50, 60, 70, 76, 81, 86, 91, 96, 101, 106, 120, 150, 200, 300, 400, 500, 700, 1000, 1500, 2000}},
        {"pTll",          {25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 130, 150, 170, 190, 220, 250, 400, 1000}},
        {"yll",           linspace(5, 0., 3)},
        {"etall",         linspace(30, -3, 3)},
        {"phill",         linspace(50, 0, 2*PI)},
        {"cosThetaCS",    linspace(20, -1, 1)},
        {"phiStar",       {0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.2, 2., 5.}},

        // Leptons, pT ordered (1 = leading, 2 = subleading)
        {"pTlep1",        {25, 35, 45, 55, 70, 90, 120, 160, 220, 400}},
        {"pTlep2",        {15, 25, 35, 45, 55, 70, 90, 120, 160, 220, 400}},
        {"etalep1",       linspace(30, -3, 3)},
        {"etalep2",       linspace(30, -3, 3)},
        {"philep1",       linspace(50, 0, 2*PI)},
        {"philep2",       linspace(50, 0, 2*PI)},

        // Leading jet, and all jets
        {"pTj",           {20, 30, 40, 50, 65, 85, 110, 150, 200, 300, 500, 1000}},
        {"absyj",         linspace(8, 0., 2.4)},
        {"yj",            linspace(6, 0., 3)},
        {"etaj",          linspace(30, -3, 3)},
        {"phij",          linspace(30, 0, 2*PI)},
        {"HT",            {20, 30, 50, 80, 120, 170, 250, 350, 500, 800, 1500}},

        // Z + leading jet system
        {"ystarZj",       linspace(6, 0., 3.0)},
        {"yboostZj",      linspace(6, 0., 3.0)},
        {"ybPlusystar",   linspace(6, 0., 3)},
        {"dPhiZj",        linspace(10, 0., PI)},
        {"zeppenfeld",    linspace(8, 0., 4.)},       // >= 2 jets, filled separately
      };

      // All variables for ee+mm; the variables for the fit also per channel, because many
      // operators act on one lepton flavour only.
      for (const auto& variable : edges) {
        bookVariable("zj_ll_" + variable.first, variable.second);
      }
      for (const string& channel : CHANNELS) {
        for (const string& variable : FIT_VARIABLES) {
          bookVariable("zj_" + channel + "_" + variable, edges.at(variable));
        }
      }
      // cos theta*_CS in mll slices, for ll and per channel: zj_<channel>_cosThetaCS_mll0 ... _mll3
      for (size_t i = 0; i < MLL_SLICES.size() - 1; ++i) {
        const string name = "cosThetaCS_mll" + to_string(i);
        bookVariable("zj_ll_" + name, edges.at("cosThetaCS"));
        for (const string& channel : CHANNELS) {
          bookVariable("zj_" + channel + "_" + name, edges.at("cosThetaCS"));
        }
      }

    // Number of jets for every Z event (0 jets -> first bin) 
    bookVariable("ll_nJets", linspace(8, -0.5, 7.5));

    // One bin per selection: 0 = all Z events, 1 = zj
    bookVariable("ll_yields", linspace(2, 0., 2.));
    }

    // Run once per event: select the event and fill the histograms
    void analyze(const Event& event) {

      // Exactly one Z candidate. Dilepton events with both flavours are dropped.
      const Particles& zee = apply<ZFinder>(event, "Zee").bosons();
      const Particles& zmm = apply<ZFinder>(event, "Zmm").bosons();
      if (zee.size() + zmm.size() != 1) vetoEvent;
      const bool is_ee = zee.size() == 1;
      const Particle& z = is_ee ? zee.front() : zmm.front();
      const string channel = is_ee ? "ee" : "mm";
      const Particles& leptons = z.constituents();  // ZFinder order: l+, then l-

      // Minimal dilepton pt cut
      if (z.pT() < PTLL_MIN) vetoEvent;
      if ((max(leptons[0].pT(), leptons[1].pT()) < LEAD_LEPTON_PT_MIN)) vetoEvent;

      // Jets in the acceptance, away from both leptons
      Jets jets = apply<FastJets>(event, "Jets").jetsByPt(Cuts::abseta < JET_ABSETA_MAX && Cuts::pT > JET_PT_MIN);
      idiscardIfAnyDeltaRLess(jets, leptons, JET_LEPTON_DR);

      _h["ll_nJets"]->fill(min(jets.size(), size_t(7)));  // 7 = overflow bin for ≥7 jets
      _h["ll_yields"]->fill(0.5);
      if (jets.empty()) vetoEvent;                        // <-- the ≥1-jet requirement

      fillVariables(channel, z, leptons, jets);
      _h["ll_yields"]->fill(1.5);
    }

    // Run once at the end: scale histograms to cross section and print summart

    /// Runs once at the end, and Rivet calls it once per weight, nominal first, then rw0000, ...
    ///
    /// The usual line, scale(_h, crossSection()/picobarn/sumW()), does not work in EFT2Obs. Each
    /// event carries two kinds of weight, and only the plain nominal one is a normal weight:
    ///  - plain nominal (e.g. zj_ll_pTll): sigma per event, so it sums to N*sigma -> divide by N
    ///  - rw weights (e.g. zj_ll_pTll[rw0000]): they already sum to sigma in pb -> keep as is.
    ///    get_scaling.py reads these.
    /// Scaling by 1 still matters: it sets the ScaledBy annotation, which makes yodamerge average
    /// the jobs. Without it, yodamerge would add up their cross sections.

    void finalize() {
      scale(_h, _finalize_calls == defaultWeightIndex() ? 1./numEvents() : 1.);
      ++_finalize_calls;
    }

  private:

    // Compute all variables for one event with at least one jet, and fill them
    void fillVariables(const string& channel, const Particle& z,
                       const Particles& leptons, const Jets& jets) {
      
      const FourMomentum Z = z.momentum();
      const FourMomentum lplus = leptons[0].momentum();
      const FourMomentum lminus = leptons[1].momentum();
      const FourMomentum J = jets.front().momentum();

      const FourMomentum& lep1 = lplus.pt() > lminus.pT() ? lplus : lminus;
      const FourMomentum& lep2 = lplus.pt() > lminus.pT() ? lminus : lplus;


      const map<string, double> values = {
        // Dilepton system (the Z)
        {"mll",          Z.mass()/GeV},
        {"pTll",         Z.pT()/GeV},
        {"yll",          Z.absrap()},                                          // |y_Z|; main analysis yZ is signed
        {"etall",        Z.eta()},                                             // pseudorapidity, NOT rapidity
        {"phill",        Z.phi()},                                             // in [0, 2pi) in Rivet
        {"cosThetaCS",   cosThetaCS(lminus, lplus)},                           // needs the charge: l-, l+
        {"phiStar",      phiStar(lminus, lplus)},

        // Leptons, pT ordered (1 = leading, 2 = subleading)
        {"pTlep1",       lep1.pT()/GeV},
        {"pTlep2",       lep2.pT()/GeV},
        {"etalep1",      lep1.eta()},
        {"etalep2",      lep2.eta()},
        {"philep1",      lep1.phi()},
        {"philep2",      lep2.phi()},

        // Leading jet, and all jets
        {"pTj",          J.pT()/GeV},
        {"absyj",        J.absrap()},
        {"yj",           J.absrap()},                                          // |y_j|, axis of main analysis yJet (signed there)
        {"etaj",         J.eta()},
        {"phij",         J.phi()},
        {"HT",           sum(jets, Kin::pT, 0.)/GeV},

        // Z + leading jet system. SMP-24-010 eqs. (1) and (2): y* follows the partonic scattering
        // angle, y_boost the imbalance of the parton momenta. Leading jet, as in the paper.
        {"ystarZj",      0.5*deltaRap(Z, J)},
        {"yboostZj",     0.5*fabs(Z.rap() + J.rap())},
        {"ybPlusystar",  max(Z.absrap(), J.absrap())},                         // = y_b + y* = max(|yZ|,|yj|)
        {"dPhiZj",       deltaPhi(Z, J)},
        // zeppenfeld: needs >= 2 jets, filled separately below
      };

      for (const auto& value : values) {
        _h["zj_ll_" + value.first]->fill(value.second);
      }
      for (const string& variable : FIT_VARIABLES) {
        _h["zj_" + channel + "_" + variable]->fill(values.at(variable));
      }

      // Zeppenfeld variable: only defined with at least 2 jets, so it is filled separately.
      if (jets.size() >= 2) {
        _h["zj_ll_zeppenfeld"]->fill(fabs(Z.rap() - 0.5*(jets[0].rap() + jets[1].rap())));
      }

      // costheta*_CS in the mll slice for this event
      const double mll = Z.mass()/GeV;
      for (size_t i = 0; i < MLL_SLICES.size() - 1; ++i) {
        if (mll < MLL_SLICES[i] || mll >= MLL_SLICES[i+1]) continue;
        const string name = "cosThetaCS_mll" + to_string(i);
        _h["zj_ll_" + name]->fill(values.at("cosThetaCS"));
        _h["zj_" + channel + "_" + name]->fill(values.at("cosThetaCS"));
        break;  // only one slice per event
      }
    }

    // cos(theta*) in the Collins-Soper frame: angle of the l- to the Z direction.
    // Rivet has no public function for this. Same formula as CMS_2013_I1122847.
    // The sign of pz(ll) is taken as the quark direction, which is correct most of the time.
    double cosThetaCS(const FourMomentum& lminus, const FourMomentum& lplus) const {
      const FourMomentum ll = lminus + lplus;
      const double Pminus_lm = lminus.E() - lminus.pz(), Pplus_lm = lminus.E() + lminus.pz();
      const double Pminus_lp = lplus.E() - lplus.pz(),   Pplus_lp = lplus.E() + lplus.pz();
      const double cosTheta = (Pplus_lm*Pminus_lp - Pminus_lm*Pplus_lp) / (ll.mass()*add_quad(ll.mass(), ll.pT()));
      return ll.pz() < 0 ? -cosTheta : cosTheta;
    }


    // phi*_eta = tan((pi - dPhi)/2) * sin(theta*_eta). Tracks pT(ll)/m(ll), but depends only
    // on the lepton directions, so it is measured very precisely.
    double phiStar(const FourMomentum& lminus, const FourMomentum& lplus) const {
      const double cosThetaEta = tanh(0.5*(lminus.eta() - lplus.eta()));
      return tan(0.5*(PI - deltaPhi(lminus, lplus))) * sqrt(1. - sqr(cosThetaEta));
    }


    // Book one histogram, stored under its name so it can be filled by name
    void bookVariable(const string& name, const vector<double>& edges) {
      book(_h[name], name, edges);
    }


    // @name Fiducial selection: change the cuts here
    // @{
    static constexpr double LEAD_LEPTON_PT_MIN = 25*GeV;  // Leading Lepton pT
    static constexpr double LEPTON_PT_MIN = 15*GeV;       // Lepton pT
    static constexpr double LEPTON_ABSETA_MAX = 2.4;      // Lepton |eta|
    static constexpr double DRESSING_DR = 0.1;            // Photon radius for dressed leptons
    static constexpr double MLL_MIN = 25*GeV;             // Dilepton mass window
    static constexpr double PTLL_MIN = 25*GeV;            // Dilepton pt
    static constexpr double MLL_MAX = 2000*GeV;           // Tighter selection later
    static constexpr double JET_R = 0.4;                  // Anti-kT radius
    static constexpr double JET_PT_MIN = 20*GeV;          // Jet pT
    static constexpr double JET_ABSETA_MAX = 2.4;         // Jet |eta|: as in PC analysis, not SMP-24-010
    static constexpr double JET_LEPTON_DR = 0.4;          // Remove jets this close to a lepton
    // @}

    const vector<string> CHANNELS = {"ee", "mm"};
    const vector<string> FIT_VARIABLES = {"pTll", "ystarZj", "yboostZj", "mll", "yll"}; // cosThetaCS in slices below
    const vector<double> MLL_SLICES = {25, 81, 101, 150, 2000}; // GeV

    // All histograms, by name
    map<string, Histo1DPtr> _h;

    // How many times finalize() has run, i.e. the index of the current weight
    size_t _finalize_calls = 0;

  };


  RIVET_DECLARE_PLUGIN(DYplusJets);

}
