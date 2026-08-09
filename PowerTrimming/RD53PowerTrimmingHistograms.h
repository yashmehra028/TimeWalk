/*!
  \file                  RD53PowerTrimmingHistograms.h
  \brief                 Header file of Power Trimming histograms
  \author                Luca GUZZI
  \version               1.0
  \date                  03/02/26
  Support:               email to luca.guzzi@cern.ch
*/

#ifndef RD53PowerTrimmingHistograms_H
#define RD53PowerTrimmingHistograms_H

#include "DQMHistogramBase.h"
#include "Utils/ContainerFactory.h"

#include <boost/range/combine.hpp>

#include <TH1F.h>

// #############
// # CONSTANTS #
// #############
#define REL_ERROR 0.01 // Relative uncertainty computed by looking at the ground drift (GNDA_REF - GND)

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

class PowerTrimmingHistograms : public DQMHistogramBase
{
    using dataType = std::vector<std::pair<uint16_t, float>>;

  public:
    PowerTrimmingHistograms() : fDetectorContainer(nullptr) {};
    ~PowerTrimmingHistograms() {};
    void book(TFile* theOutputFile, DetectorContainer& theDetectorStructure, const Ph2_Parser::SettingsMap& settingsMap) override;
    void process() override;
    bool fill(std::string& inputStream) override;
    void reset() override {};

    void fillPreamplifierCurrentHisto(const DetectorDataContainer& dataContainer);
    void fillComparatorCurrentHisto(const DetectorDataContainer& dataContainer);
    void fillLDACCurrentHisto(const DetectorDataContainer& dataContainer);
    void fillCustomHistos(const std::vector<PowerTrimmingData>& dataList);

    bool AreHistoBooked = false;

  private:
    DetectorContainer* fDetectorContainer;

    std::vector<std::shared_ptr<DetectorDataContainer>> PreamplifiersCurrent;
    std::vector<std::shared_ptr<DetectorDataContainer>> ComparatorsCurrent;
    DetectorDataContainer                               LDACCurrent;

    DetectorDataContainer theChipCurrVsTimeContainer;
    DetectorDataContainer theAnaInVsTimeContainer;
    DetectorDataContainer theDigInVsTimeContainer;
    DetectorDataContainer theAnaShuntVsTimeContainer;
    DetectorDataContainer theDigShuntVsTimeContainer;
    DetectorDataContainer theVINAVsTimeContainer;
    DetectorDataContainer theVDDAVsTimeContainer;
    DetectorDataContainer theVINDVsTimeContainer;
    DetectorDataContainer theVDDDVsTimeContainer;
    DetectorDataContainer theIrefVsTimeContainer;
    DetectorDataContainer theInternalNTCRelContainer;
    DetectorDataContainer theInternalNTCAbsContainer;
    DetectorDataContainer thePolyTempSensTopContainer;
    DetectorDataContainer thePolyTempSensBottomContainer;
    DetectorDataContainer theTempsensAnaSldoContainer;
    DetectorDataContainer theTempsensDigSldoContainer;
    DetectorDataContainer theTempsensCenterContainer;
};

#endif
