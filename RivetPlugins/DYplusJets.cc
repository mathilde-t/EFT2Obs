// -*- C++ -*-
//
// DYplusJets: differential cross sections for pp -> Z/gamma*(-> ee, mumu) + jets, inclusive
// in the jets and vs the number of jets, for EFT2Obs SMEFT studies. No jet flavour tagging.
//
// EFT2Obs gives every event one weight per reweighting point, and Rivet fills each histogram
// once per weight. get_scaling.py then turns those histograms into per-bin SMEFT scaling
// functions, so nothing in this routine is SMEFT-specific.
//
// Observables: y*, y_boost and the pT(ll) and rapidity binning are from the CMS Z+jet
// triple-differential measurement, CMS-PAS-SMP-24-010, which does not use cos(theta*).
// Object cuts: from the CMS Z+c/b routine in Rivet (CMS_2020_I1776758, SMP-19-004), because
// SMP-24-010 is mumu only. Its cuts differ: lepton pT > 29 GeV, jet pT > 20 GeV and
// pT(ll) > 25 GeV. The tagging itself is not used here.
// All cuts are at particle level, with no detector effects.
//
// Histogram names: zj_<channel>_<variable>, e.g. zj_ll_pTll. zj = at least 1 jet.
//   channel: ee, mm, ll (ll = ee + mm)
//   The "jet" in Z-jet variables is the leading jet.
// ll_nJets has every Z event, including those with no jet.
//
// Every histogram costs about (bins x 596 weights) in the output file, so the ee and mm
// channels only get the variables listed in FIT_VARIABLES.
//
#include "Rivet/Analysis.hh"
#include "Rivet/Projections/FinalState.hh"
#include "Rivet/Projections/FastJets.hh"
#include "Rivet/Projections/VetoedFinalState.hh"
#include "Rivet/Projections/ZFinder.hh"

namespace Rivet {


  class DYplusJets : public Analysis {
  public:

    RIVET_DEFAULT_ANALYSIS_CTOR(DYplusJets);


    /// Runs once at the start: declare the projections and book the histograms
    void init() {

      // A Z candidate is an opposite-sign, same-flavour pair of prompt dressed leptons in the
      // mass window. One ZFinder per flavour: this is the main selection, and it does the
      // dressing, prompt selection and pairing that DY_EE.cc does by hand.
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

      // Bin edges per variable. No measurement exists yet, so the edges are given here instead
      // of being read from a reference .yoda file with refData().
      const map<string, vector<double>> edges = {
        // Dilepton system
        {"mll",        linspace(20, MLL_MIN/GeV, MLL_MAX/GeV)},
        // SMP-24-010 "central" pT(Z) edges from 25 GeV, plus 2 bins below (it cuts pT(ll) > 25 GeV)
        {"pTll",       {0, 10, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 130, 150, 170, 190, 220, 250, 400, 1000}},
        {"absyll",     linspace(12, 0., 2.4)},
        {"cosThetaCS", linspace(10, -1., 1.)},
        {"phiStar",    {0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.2, 2., 5.}},
        {"pTlep1",     {25, 35, 45, 55, 70, 90, 120, 160, 220, 400}},
        // Jets
        {"pTj",        {30, 40, 50, 65, 85, 110, 150, 200, 300, 500, 1000}},
        {"absyj",      linspace(8, 0., 2.4)},
        {"HT",         {30, 50, 80, 120, 170, 250, 350, 500, 800, 1500}},
        // Z-jet system
        {"ystarZj",    linspace(5, 0., 2.5)},   // SMP-24-010: steps of 0.5
        {"yboostZj",   linspace(5, 0., 2.5)},   // SMP-24-010: steps of 0.5
        {"dPhiZj",     linspace(10, 0., PI)},
        {"mZj",        {100, 150, 200, 250, 300, 400, 500, 700, 1000, 1500, 3000}},
        {"zeppenfeld", linspace(8, 0., 4.)}
      };

      // All variables for ee+mm; the variables for the fit also per channel, because many
      // operators act on one lepton flavour only (e.g. che11 vs che22).
      for (const auto& variable : edges) {
        bookVariable("zj_ll_" + variable.first, variable.second);
      }
      for (const string& channel : CHANNELS) {
        for (const string& variable : FIT_VARIABLES) {
          bookVariable("zj_" + channel + "_" + variable, edges.at(variable));
        }
      }

      // Number of jets for every Z event, including those with no jet (first bin)
      bookVariable("ll_nJets", linspace(6, -0.5, 5.5));
      // One bin per selection: 0 = all Z events, 1 = zj
      bookVariable("ll_yields", linspace(2, 0., 2.));
    }


    /// Runs once per event: select the event and fill the histograms
    void analyze(const Event& event) {

      // Exactly one Z candidate. Dilepton events with both flavours are dropped.
      const Particles& zee = apply<ZFinder>(event, "Zee").bosons();
      const Particles& zmm = apply<ZFinder>(event, "Zmm").bosons();
      if (zee.size() + zmm.size() != 1) vetoEvent;
      const bool is_ee = zee.size() == 1;
      const Particle& z = is_ee ? zee.front() : zmm.front();
      const string channel = is_ee ? "ee" : "mm";
      const Particles& leptons = z.constituents();  // ZFinder order: l+, then l-

      // Jets in the acceptance, away from both leptons
      Jets jets = apply<FastJets>(event, "Jets").jetsByPt(Cuts::absrap < JET_ABSY_MAX && Cuts::pT > JET_PT_MIN);
      idiscardIfAnyDeltaRLess(jets, leptons, JET_LEPTON_DR);

      _h["ll_nJets"]->fill(min(jets.size(), size_t(5)));
      _h["ll_yields"]->fill(0.5);
      if (jets.empty()) vetoEvent;

      fillVariables(channel, z, leptons, jets);
      _h["ll_yields"]->fill(1.5);
    }


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

    /// Compute all variables for one event with at least one jet, and fill them
    void fillVariables(const string& channel, const Particle& z,
                       const Particles& leptons, const Jets& jets) {

      const FourMomentum Z = z.momentum();
      const FourMomentum lplus = leptons[0].momentum();
      const FourMomentum lminus = leptons[1].momentum();
      const FourMomentum J = jets.front().momentum();

      const map<string, double> values = {
        {"mll",        Z.mass()/GeV},
        {"pTll",       Z.pT()/GeV},
        {"absyll",     Z.absrap()},
        {"cosThetaCS", cosThetaCS(lminus, lplus)},
        {"phiStar",    phiStar(lminus, lplus)},
        {"pTlep1",     max(lminus.pT(), lplus.pT())/GeV},
        {"pTj",        J.pT()/GeV},
        {"absyj",      J.absrap()},
        {"HT",         sum(jets, Kin::pT, 0.)/GeV},
        // SMP-24-010 eqs. (1) and (2). y* follows the partonic scattering angle and y_boost the
        // imbalance of the parton momenta. Leading jet, as in the paper.
        {"ystarZj",    0.5*deltaRap(Z, J)},
        {"yboostZj",   0.5*fabs(Z.rap() + J.rap())},
        {"dPhiZj",     deltaPhi(Z, J)},
        {"mZj",        (Z + J).mass()/GeV}
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
    }


    /// cos(theta*) in the Collins-Soper frame: angle of the l- to the Z direction.
    /// Rivet has no public function for this. Same formula as CMS_2013_I1122847.
    /// The sign of pz(ll) is taken as the quark direction, which is correct most of the time.
    double cosThetaCS(const FourMomentum& lminus, const FourMomentum& lplus) const {
      const FourMomentum ll = lminus + lplus;
      const double Pminus_lm = lminus.E() - lminus.pz(), Pplus_lm = lminus.E() + lminus.pz();
      const double Pminus_lp = lplus.E() - lplus.pz(),   Pplus_lp = lplus.E() + lplus.pz();
      const double cosTheta = (Pplus_lm*Pminus_lp - Pminus_lm*Pplus_lp) / (ll.mass()*add_quad(ll.mass(), ll.pT()));
      return ll.pz() < 0 ? -cosTheta : cosTheta;
    }


    /// phi*_eta = tan((pi - dPhi)/2) * sin(theta*_eta). Tracks pT(ll)/m(ll), but depends only
    /// on the lepton directions, so it is measured very precisely.
    double phiStar(const FourMomentum& lminus, const FourMomentum& lplus) const {
      const double cosThetaEta = tanh(0.5*(lminus.eta() - lplus.eta()));
      return tan(0.5*(PI - deltaPhi(lminus, lplus))) * sqrt(1. - sqr(cosThetaEta));
    }


    /// Book one histogram, stored under its name so it can be filled by name
    void bookVariable(const string& name, const vector<double>& edges) {
      book(_h[name], name, edges);
    }


    /// @name Fiducial selection: change the cuts here
    /// @{
    static constexpr double LEPTON_PT_MIN = 25*GeV;      // Lepton pT
    static constexpr double LEPTON_ABSETA_MAX = 2.4;     // Lepton |eta|
    static constexpr double DRESSING_DR = 0.1;           // Photon radius for dressed leptons
    static constexpr double MLL_MIN = 71*GeV;            // Dilepton mass window
    static constexpr double MLL_MAX = 111*GeV;
    static constexpr double JET_R = 0.4;                 // Anti-kT radius
    static constexpr double JET_PT_MIN = 30*GeV;         // Jet pT
    static constexpr double JET_ABSY_MAX = 2.4;          // Jet |y|: as in SMP-24-010
    static constexpr double JET_LEPTON_DR = 0.4;         // Remove jets this close to a lepton
    /// @}

    const vector<string> CHANNELS = {"ee", "mm"};
    const vector<string> FIT_VARIABLES = {"pTll", "absyll", "cosThetaCS", "ystarZj", "yboostZj"};

    /// All histograms, by name
    map<string, Histo1DPtr> _h;

    /// How many times finalize() has run, i.e. the index of the current weight
    size_t _finalize_calls = 0;

  };


  RIVET_DECLARE_PLUGIN(DYplusJets);

}
