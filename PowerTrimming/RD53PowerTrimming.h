/*!
  \file                  RD53PowerTrimming.h
  \brief                 Header of power trimming
  \author                Luca GUZZI
  \version               1.0
  \date                  27/01/26
  Support:               email to luca.guzzi@cern.ch
*/

#ifndef RD53PowerTrimming_H
#define RD53PowerTrimming_H

#include "RD53CalibBase.h"

#ifdef __USE_ROOT__
#include "DQMUtils/RD53PowerTrimmingHistograms.h"
#else
typedef bool PowerTrimmingHistograms;
struct PowerTrimmingData
{
    double   timestamp            = 0;
    uint16_t bit                  = 0;
    float    ChipCurrent          = 0;
    float    ANA_IN_CURR          = 0;
    float    DIG_IN_CURR          = 0;
    float    VINA                 = 0;
    float    VDDA                 = 0;
    float    VIND                 = 0;
    float    VDDD                 = 0;
    float    Iref                 = 0;
    float    ANA_SHUNT_CURR       = 0;
    float    DIG_SHUNT_CURR       = 0;
    float    INTERNAL_NTC_REL     = 0;
    float    INTERNAL_NTC_ABS     = 0;
    float    POLY_TEMPSENS_TOP    = 0;
    float    POLY_TEMPSENS_BOTTOM = 0;
    float    TEMPSENS_ANA_SLDO    = 0;
    float    TEMPSENS_DIG_SLDO    = 0;
    float    TEMPSENS_CENTER      = 0;
};
#endif

class PowerTrimming : public CalibBase
{
  public:
    ~PowerTrimming()
    {
        WriteRootFile();
        delete histos;
    }

    void Running() override;
    void Stop() override;
    void ConfigureCalibration() override;
    void sendData() override;
    void run() override;
    void draw(bool saveData = true) override;
    void localConfigure(const std::string& histoFileName, int currentRun) override;
    void analyze();

    PowerTrimmingHistograms* histos;

  private:
    void fillHisto() override;
    void linearScanBottomUp(Ph2_HwDescription::RD53* pChip, const std::vector<const char*>& regNames, uint16_t startValue, uint16_t maxValue, float& targetDiff, const uint16_t COMPdefaultVal);

    uint16_t   MAX_PREAMP;
    uint16_t   MAX_COMP;
    uint16_t   MAX_LDAC;
    const bool doDebug{true};

    std::vector<PowerTrimmingData> fPowerTrimmingResults;

    DetectorDataContainer theComparatorCurrentContainer;
    DetectorDataContainer thePreamplifierCurrentContainer;
    DetectorDataContainer theLDACCurrentContainer;

  protected:
    // ######################################
    // # Parameters from configuration file #
    // ######################################
    float PREAMP_CURRENT_mA;
    float COMP_CURRENT_mA;
    float LDAC_CURRENT_mA;
    bool  doDisplay;
    bool  doUpdateChip;

    // ####################
    // # Monitor switches #
    // ####################
    float mon_DIG_IN_CURR;
    float mon_DIG_SHUNT_CURR;
    float mon_VINA;
    float mon_VDDA;
    float mon_VIND;
    float mon_VDDD;
    float mon_Iref;
    float mon_INTERNAL_NTC_REL;
    float mon_INTERNAL_NTC_ABS;
    float mon_POLY_TEMPSENS_TOP;
    float mon_POLY_TEMPSENS_BOTTOM;
    float mon_TEMPSENS_ANA_SLDO;
    float mon_TEMPSENS_DIG_SLDO;
    float mon_TEMPSENS_CENTER;
};

#endif
