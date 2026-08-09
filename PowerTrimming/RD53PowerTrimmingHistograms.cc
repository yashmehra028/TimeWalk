/*!
  \file                  RD53PowerTrimmingHistograms.cc
  \brief                 Source file of Power Trimming histograms
  \author                Luca GUZZI
  \version               1.0
  \date                  03/02/26
  \support               email to luca.guzzi@cern.ch
*/

#include "RD53PowerTrimmingHistograms.h"
#include "Utils/ContainerSerialization.h"

using namespace Ph2_HwDescription;

void PowerTrimmingHistograms::book(TFile* theOutputFile, DetectorContainer& theDetectorStructure, const Ph2_Parser::SettingsMap& settingsMap)
{
    fDetectorContainer = &theDetectorStructure;
    RD53Shared::setFirstChip(theDetectorStructure);

    // #######################
    // # Retrieve parameters #
    // #######################
    auto           frontEnd = RD53Shared::firstChip->getFEtype(RD53Shared::firstChip->getNCols() / 2, RD53Shared::firstChip->getNCols() / 2);
    const uint16_t maxVal   = RD53Shared::setBits(RD53Shared::firstChip->getNumberOfBits("DAC_PREAMP_M_LIN")) + 1;

    // #######################
    // # Standard histograms #
    // #######################

    // ################
    // # Preamplifier #
    // ################
    std::vector<CanvasContainer<TH1F>> hPreampsCurr;
    for(const auto& regName: frontEnd->preampRegs) hPreampsCurr.emplace_back(regName, "Preamplifier current", maxVal, 0, maxVal);
    for(const auto& [hPreamp, regName]: boost::combine(hPreampsCurr, frontEnd->preampRegs))
    {
        PreamplifiersCurrent.push_back(std::make_shared<DetectorDataContainer>());
        bookChipImplementer(theOutputFile, theDetectorStructure, *PreamplifiersCurrent.back(), hPreamp, regName, "Entries");
    }
    hPreampsCurr.emplace_back("DAC_FC_LIN", "Preamplifier current", maxVal, 0, maxVal);
    PreamplifiersCurrent.push_back(std::make_shared<DetectorDataContainer>());
    bookChipImplementer(theOutputFile, theDetectorStructure, *PreamplifiersCurrent.back(), hPreampsCurr.back(), "DAC_FC_LIN", "Entries");

    // ##############
    // # Comparator #
    // ##############
    std::vector<CanvasContainer<TH1F>> hCompsCurr;
    hCompsCurr.emplace_back("DAC_COMP_LIN", "Comparator current", maxVal, 0, maxVal);
    hCompsCurr.emplace_back("DAC_COMP_TA_LIN", "Comparator current", maxVal, 0, maxVal);
    ComparatorsCurrent.push_back(std::make_shared<DetectorDataContainer>());
    ComparatorsCurrent.push_back(std::make_shared<DetectorDataContainer>());
    bookChipImplementer(theOutputFile, theDetectorStructure, *ComparatorsCurrent.at(0), hCompsCurr.at(0), "DAC_COMP_LIN", "Entries");
    bookChipImplementer(theOutputFile, theDetectorStructure, *ComparatorsCurrent.at(1), hCompsCurr.at(1), "DAC_COMP_TA_LIN", "Entries");

    // ########
    // # LDAC #
    // ########
    auto hLDACCurrent = CanvasContainer<TH1F>("LDACCurrent", "LDAC current", maxVal, 0, maxVal);
    bookChipImplementer(theOutputFile, theDetectorStructure, LDACCurrent, hLDACCurrent, "LDAC current", "Entries");

    // ########################
    // # Debugging histograms #
    // ########################
    auto hChipCurrVsTime   = CanvasContainer<TH1F>("ChipCurrent", "Total chip current vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hIAnaVsTime       = CanvasContainer<TH1F>("ANA_IN_CURR", "Analog current vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hIDigVsTime       = CanvasContainer<TH1F>("DIG_IN_CURR", "Digital current vs Time", 3 * maxVal, 0, maxVal);
    auto hAnaShuntVsTime   = CanvasContainer<TH1F>("ANA_SHUNT_CURR", "Analog Shunt current vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hDigShuntVsTime   = CanvasContainer<TH1F>("DIG_SHUNT_CURR", "Digital Shunt current vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hVAnaVsTime       = CanvasContainer<TH1F>("VINA", "VINA vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hVDAnaVsTime      = CanvasContainer<TH1F>("VDDA", "VDDA vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hVDigVsTime       = CanvasContainer<TH1F>("VIND", "VIND vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hVDDigVsTime      = CanvasContainer<TH1F>("VDDD", "VDDD vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hIrfVsTime        = CanvasContainer<TH1F>("Iref", "Iref vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hNTCrelVsTime     = CanvasContainer<TH1F>("INTERNAL_NTC_REL", "INTERNAL_NTC_REL vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hNTCabsVsTime     = CanvasContainer<TH1F>("INTERNAL_NTC_ABS", "INTERNAL_NTC_ABS vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hPolyTopVsTime    = CanvasContainer<TH1F>("POLY_TEMPSENS_TOP", "POLY_TEMPSENS_TOP vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hPolyBottomVsTime = CanvasContainer<TH1F>("POLY_TEMPSENS_BOTTOM", "POLY_TEMPSENS_BOTTOM vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hSLDOAnaVsTime    = CanvasContainer<TH1F>("TEMPSENS_ANA_SLDO", "TEMPSENS_ANA_SLDO vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hSLDODigVsTime    = CanvasContainer<TH1F>("TEMPSENS_DIG_SLDO", "TEMPSENS_DIG_SLDO vs Time", 3 * maxVal, 0, 3 * maxVal);
    auto hSLDOCenterVsTime = CanvasContainer<TH1F>("TEMPSENS_CENTER", "TEMPSENS_CENTER vs Time", 3 * maxVal, 0, 3 * maxVal);

    bookChipImplementer(theOutputFile, theDetectorStructure, theChipCurrVsTimeContainer, hChipCurrVsTime, "Time (HH:MM:SS)", "Current (mA)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theAnaInVsTimeContainer, hIAnaVsTime, "Time (HH:MM:SS)", "Current (mA)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theDigInVsTimeContainer, hIDigVsTime, "Time (HH:MM:SS)", "Current (mA)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theAnaShuntVsTimeContainer, hAnaShuntVsTime, "Time (HH:MM:SS)", "Current (mA)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theDigShuntVsTimeContainer, hDigShuntVsTime, "Time (HH:MM:SS)", "Current (mA)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theVINAVsTimeContainer, hVAnaVsTime, "Time (HH:MM:SS)", "Voltage (V)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theVDDAVsTimeContainer, hVDAnaVsTime, "Time (HH:MM:SS)", "Voltage (V)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theVINDVsTimeContainer, hVDigVsTime, "Time (HH:MM:SS)", "Voltage (V)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theVDDDVsTimeContainer, hVDDigVsTime, "Time (HH:MM:SS)", "Voltage (V)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theIrefVsTimeContainer, hIrfVsTime, "Time (HH:MM:SS)", "Iref (uA)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theInternalNTCRelContainer, hNTCrelVsTime, "Time (HH:MM:SS)", "Temperature (C)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theInternalNTCAbsContainer, hNTCabsVsTime, "Time (HH:MM:SS)", "Temperature (C)");
    bookChipImplementer(theOutputFile, theDetectorStructure, thePolyTempSensTopContainer, hPolyTopVsTime, "Time (HH:MM:SS)", "Temperature (C)");
    bookChipImplementer(theOutputFile, theDetectorStructure, thePolyTempSensBottomContainer, hPolyBottomVsTime, "Time (HH:MM:SS)", "Temperature (C)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theTempsensAnaSldoContainer, hSLDOAnaVsTime, "Time (HH:MM:SS)", "Temperature (C)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theTempsensDigSldoContainer, hSLDODigVsTime, "Time (HH:MM:SS)", "Temperature (C)");
    bookChipImplementer(theOutputFile, theDetectorStructure, theTempsensCenterContainer, hSLDOCenterVsTime, "Time (HH:MM:SS)", "Temperature (C)");

    AreHistoBooked = true;
}

bool PowerTrimmingHistograms::fill(std::string& inputStream)
{
    ContainerSerialization thePreamplifierCurrentSerialization("PowerTrimmingPreamplifierCurrent");
    ContainerSerialization theComparatorCurrentSerialization("PowerTrimmingComparatorCurrent");
    ContainerSerialization theLDACCurrentSerialization("PowerTrimmingLDACCurrent");

    if(thePreamplifierCurrentSerialization.attachDeserializer(inputStream))
    {
        DetectorDataContainer fDetectorData = thePreamplifierCurrentSerialization.deserializeChipContainer<EmptyContainer, dataType>(fDetectorContainer);
        PowerTrimmingHistograms::fillPreamplifierCurrentHisto(fDetectorData);
        return true;
    }
    if(theComparatorCurrentSerialization.attachDeserializer(inputStream))
    {
        DetectorDataContainer fDetectorData = theComparatorCurrentSerialization.deserializeChipContainer<EmptyContainer, dataType>(fDetectorContainer);
        PowerTrimmingHistograms::fillComparatorCurrentHisto(fDetectorData);
        return true;
    }
    if(theLDACCurrentSerialization.attachDeserializer(inputStream))
    {
        DetectorDataContainer fDetectorData = theLDACCurrentSerialization.deserializeChipContainer<EmptyContainer, dataType>(fDetectorContainer);
        PowerTrimmingHistograms::fillLDACCurrentHisto(fDetectorData);
        return true;
    }
    return false;
}

void PowerTrimmingHistograms::fillPreamplifierCurrentHisto(const DetectorDataContainer& dataContainer)
{
    for(const auto cBoard: dataContainer)
        for(const auto cOpticalGroup: *cBoard)
            for(const auto cHybrid: *cOpticalGroup)
                for(const auto cChip: *cHybrid)
                {
                    if(cChip->hasSummary() == false) continue;

                    for(auto i = 0u; i < PreamplifiersCurrent.size(); i++)
                    {
                        auto* histo = PreamplifiersCurrent.at(i)
                                          ->getObject(cBoard->getId())
                                          ->getObject(cOpticalGroup->getId())
                                          ->getObject(cHybrid->getId())
                                          ->getObject(cChip->getId())
                                          ->getSummary<CanvasContainer<TH1F>>()
                                          .fTheHistogram;

                        histo->Fill(cChip->getSummary<std::vector<uint16_t>>().at(i));
                    }

                    auto* histo = PreamplifiersCurrent.back()
                                      ->getObject(cBoard->getId())
                                      ->getObject(cOpticalGroup->getId())
                                      ->getObject(cHybrid->getId())
                                      ->getObject(cChip->getId())
                                      ->getSummary<CanvasContainer<TH1F>>()
                                      .fTheHistogram;

                    histo->Fill(cChip->getSummary<std::vector<uint16_t>>().back());
                }
}

void PowerTrimmingHistograms::fillComparatorCurrentHisto(const DetectorDataContainer& dataContainer)
{
    for(const auto cBoard: dataContainer)
        for(const auto cOpticalGroup: *cBoard)
            for(const auto cHybrid: *cOpticalGroup)
                for(const auto cChip: *cHybrid)
                {
                    if(cChip->hasSummary() == false) continue;

                    auto* histo = ComparatorsCurrent.at(0)
                                      ->getObject(cBoard->getId())
                                      ->getObject(cOpticalGroup->getId())
                                      ->getObject(cHybrid->getId())
                                      ->getObject(cChip->getId())
                                      ->getSummary<CanvasContainer<TH1F>>()
                                      .fTheHistogram;

                    histo->Fill(cChip->getSummary<std::vector<uint16_t>>().at(0));

                    histo = ComparatorsCurrent.at(1)
                                ->getObject(cBoard->getId())
                                ->getObject(cOpticalGroup->getId())
                                ->getObject(cHybrid->getId())
                                ->getObject(cChip->getId())
                                ->getSummary<CanvasContainer<TH1F>>()
                                .fTheHistogram;

                    histo->Fill(cChip->getSummary<std::vector<uint16_t>>().at(1));
                }
}

void PowerTrimmingHistograms::fillLDACCurrentHisto(const DetectorDataContainer& dataContainer)
{
    for(const auto cBoard: dataContainer)
        for(const auto cOpticalGroup: *cBoard)
            for(const auto cHybrid: *cOpticalGroup)
                for(const auto cChip: *cHybrid)
                {
                    if(cChip->hasSummary() == false) continue;

                    auto* histo = LDACCurrent.getObject(cBoard->getId())
                                      ->getObject(cOpticalGroup->getId())
                                      ->getObject(cHybrid->getId())
                                      ->getObject(cChip->getId())
                                      ->getSummary<CanvasContainer<TH1F>>()
                                      .fTheHistogram;

                    histo->Fill(cChip->getSummary<uint16_t>());
                }
}

void PowerTrimmingHistograms::fillCustomHistos(const std::vector<PowerTrimmingData>& dataList)
{
    if(dataList.empty()) return;

    for(const auto cBoard: *fDetectorContainer)
        for(const auto cOpticalGroup: *cBoard)
            for(const auto cHybrid: *cOpticalGroup)
                for(const auto cChip: *cHybrid)
                {
                    auto* hChipCurr = theChipCurrVsTimeContainer.getObject(cBoard->getId())
                                          ->getObject(cOpticalGroup->getId())
                                          ->getObject(cHybrid->getId())
                                          ->getObject(cChip->getId())
                                          ->getSummary<CanvasContainer<TH1F>>()
                                          .fTheHistogram;
                    auto* hIAna = theAnaInVsTimeContainer.getObject(cBoard->getId())
                                      ->getObject(cOpticalGroup->getId())
                                      ->getObject(cHybrid->getId())
                                      ->getObject(cChip->getId())
                                      ->getSummary<CanvasContainer<TH1F>>()
                                      .fTheHistogram;
                    auto* hIDig = theDigInVsTimeContainer.getObject(cBoard->getId())
                                      ->getObject(cOpticalGroup->getId())
                                      ->getObject(cHybrid->getId())
                                      ->getObject(cChip->getId())
                                      ->getSummary<CanvasContainer<TH1F>>()
                                      .fTheHistogram;
                    auto* hAnaShunt = theAnaShuntVsTimeContainer.getObject(cBoard->getId())
                                          ->getObject(cOpticalGroup->getId())
                                          ->getObject(cHybrid->getId())
                                          ->getObject(cChip->getId())
                                          ->getSummary<CanvasContainer<TH1F>>()
                                          .fTheHistogram;
                    auto* hDigShunt = theDigShuntVsTimeContainer.getObject(cBoard->getId())
                                          ->getObject(cOpticalGroup->getId())
                                          ->getObject(cHybrid->getId())
                                          ->getObject(cChip->getId())
                                          ->getSummary<CanvasContainer<TH1F>>()
                                          .fTheHistogram;
                    auto* hVinAna = theVINAVsTimeContainer.getObject(cBoard->getId())
                                        ->getObject(cOpticalGroup->getId())
                                        ->getObject(cHybrid->getId())
                                        ->getObject(cChip->getId())
                                        ->getSummary<CanvasContainer<TH1F>>()
                                        .fTheHistogram;
                    auto* hVDAna = theVDDAVsTimeContainer.getObject(cBoard->getId())
                                       ->getObject(cOpticalGroup->getId())
                                       ->getObject(cHybrid->getId())
                                       ->getObject(cChip->getId())
                                       ->getSummary<CanvasContainer<TH1F>>()
                                       .fTheHistogram;
                    auto* hVinDig = theVINDVsTimeContainer.getObject(cBoard->getId())
                                        ->getObject(cOpticalGroup->getId())
                                        ->getObject(cHybrid->getId())
                                        ->getObject(cChip->getId())
                                        ->getSummary<CanvasContainer<TH1F>>()
                                        .fTheHistogram;
                    auto* hVDDig = theVDDDVsTimeContainer.getObject(cBoard->getId())
                                       ->getObject(cOpticalGroup->getId())
                                       ->getObject(cHybrid->getId())
                                       ->getObject(cChip->getId())
                                       ->getSummary<CanvasContainer<TH1F>>()
                                       .fTheHistogram;
                    auto* hIrf = theIrefVsTimeContainer.getObject(cBoard->getId())
                                     ->getObject(cOpticalGroup->getId())
                                     ->getObject(cHybrid->getId())
                                     ->getObject(cChip->getId())
                                     ->getSummary<CanvasContainer<TH1F>>()
                                     .fTheHistogram;
                    auto* hNTCrel = theInternalNTCRelContainer.getObject(cBoard->getId())
                                        ->getObject(cOpticalGroup->getId())
                                        ->getObject(cHybrid->getId())
                                        ->getObject(cChip->getId())
                                        ->getSummary<CanvasContainer<TH1F>>()
                                        .fTheHistogram;
                    auto* hNTCabs = theInternalNTCAbsContainer.getObject(cBoard->getId())
                                        ->getObject(cOpticalGroup->getId())
                                        ->getObject(cHybrid->getId())
                                        ->getObject(cChip->getId())
                                        ->getSummary<CanvasContainer<TH1F>>()
                                        .fTheHistogram;
                    auto* hPTT = thePolyTempSensTopContainer.getObject(cBoard->getId())
                                     ->getObject(cOpticalGroup->getId())
                                     ->getObject(cHybrid->getId())
                                     ->getObject(cChip->getId())
                                     ->getSummary<CanvasContainer<TH1F>>()
                                     .fTheHistogram;
                    auto* hPTB = thePolyTempSensBottomContainer.getObject(cBoard->getId())
                                     ->getObject(cOpticalGroup->getId())
                                     ->getObject(cHybrid->getId())
                                     ->getObject(cChip->getId())
                                     ->getSummary<CanvasContainer<TH1F>>()
                                     .fTheHistogram;
                    auto* hSLDOAna = theTempsensAnaSldoContainer.getObject(cBoard->getId())
                                         ->getObject(cOpticalGroup->getId())
                                         ->getObject(cHybrid->getId())
                                         ->getObject(cChip->getId())
                                         ->getSummary<CanvasContainer<TH1F>>()
                                         .fTheHistogram;
                    auto* hSLDODig = theTempsensDigSldoContainer.getObject(cBoard->getId())
                                         ->getObject(cOpticalGroup->getId())
                                         ->getObject(cHybrid->getId())
                                         ->getObject(cChip->getId())
                                         ->getSummary<CanvasContainer<TH1F>>()
                                         .fTheHistogram;
                    auto* hSLDOCen = theTempsensCenterContainer.getObject(cBoard->getId())
                                         ->getObject(cOpticalGroup->getId())
                                         ->getObject(cHybrid->getId())
                                         ->getObject(cChip->getId())
                                         ->getSummary<CanvasContainer<TH1F>>()
                                         .fTheHistogram;

                    hChipCurr->SetMarkerStyle(20);
                    hChipCurr->SetMarkerSize(0.8);
                    hIAna->SetMarkerStyle(20);
                    hIAna->SetMarkerSize(0.8);
                    hIDig->SetMarkerStyle(20);
                    hIDig->SetMarkerSize(0.8);
                    hAnaShunt->SetMarkerStyle(20);
                    hAnaShunt->SetMarkerSize(0.8);
                    hDigShunt->SetMarkerStyle(20);
                    hDigShunt->SetMarkerSize(0.8);
                    hVinAna->SetMarkerStyle(20);
                    hVinAna->SetMarkerSize(0.8);
                    hVDAna->SetMarkerStyle(20);
                    hVDAna->SetMarkerSize(0.8);
                    hVinDig->SetMarkerStyle(20);
                    hVinDig->SetMarkerSize(0.8);
                    hVDDig->SetMarkerStyle(20);
                    hVDDig->SetMarkerSize(0.8);
                    hIrf->SetMarkerStyle(20);
                    hIrf->SetMarkerSize(0.8);
                    hNTCrel->SetMarkerStyle(20);
                    hNTCrel->SetMarkerSize(0.8);
                    hNTCabs->SetMarkerStyle(20);
                    hNTCabs->SetMarkerSize(0.8);
                    hPTT->SetMarkerStyle(20);
                    hPTT->SetMarkerSize(0.8);
                    hPTB->SetMarkerStyle(20);
                    hPTB->SetMarkerSize(0.8);
                    hSLDOAna->SetMarkerStyle(20);
                    hSLDOAna->SetMarkerSize(0.8);
                    hSLDODig->SetMarkerStyle(20);
                    hSLDODig->SetMarkerSize(0.8);
                    hSLDOCen->SetMarkerStyle(20);
                    hSLDOCen->SetMarkerSize(0.8);

                    double   start_time   = -1.0;
                    uint16_t step_counter = 0;

                    for(const auto& data: dataList)
                    {
                        const uint16_t binX = ++step_counter;

                        hChipCurr->SetBinContent(binX, data.ChipCurrent);
                        hChipCurr->SetBinError(binX, data.ChipCurrent * REL_ERROR);
                        hIAna->SetBinContent(binX, data.ANA_IN_CURR);
                        hIAna->SetBinError(binX, data.ANA_IN_CURR * REL_ERROR);
                        hIDig->SetBinContent(binX, data.DIG_IN_CURR);
                        hIDig->SetBinError(binX, data.DIG_IN_CURR * REL_ERROR);
                        hAnaShunt->SetBinContent(binX, data.ANA_SHUNT_CURR);
                        hAnaShunt->SetBinError(binX, data.ANA_SHUNT_CURR * REL_ERROR);
                        hDigShunt->SetBinContent(binX, data.DIG_SHUNT_CURR);
                        hDigShunt->SetBinError(binX, data.DIG_SHUNT_CURR * REL_ERROR);
                        hVinAna->SetBinContent(binX, data.VINA);
                        hVinAna->SetBinError(binX, data.VINA * REL_ERROR);
                        hVDAna->SetBinContent(binX, data.VDDA);
                        hVDAna->SetBinError(binX, data.VDDA * REL_ERROR);
                        hVinDig->SetBinContent(binX, data.VIND);
                        hVinDig->SetBinError(binX, data.VIND * REL_ERROR);
                        hVDDig->SetBinContent(binX, data.VDDD);
                        hVDDig->SetBinError(binX, data.VDDD * REL_ERROR);
                        hIrf->SetBinContent(binX, data.Iref);
                        hIrf->SetBinError(binX, data.Iref * REL_ERROR);
                        hNTCrel->SetBinContent(binX, data.INTERNAL_NTC_REL);
                        hNTCrel->SetBinError(binX, data.INTERNAL_NTC_REL * REL_ERROR);
                        hNTCabs->SetBinContent(binX, data.INTERNAL_NTC_ABS);
                        hNTCabs->SetBinError(binX, data.INTERNAL_NTC_ABS * REL_ERROR);
                        hPTT->SetBinContent(binX, data.POLY_TEMPSENS_TOP);
                        hPTT->SetBinError(binX, data.POLY_TEMPSENS_TOP * REL_ERROR);
                        hPTB->SetBinContent(binX, data.POLY_TEMPSENS_BOTTOM);
                        hPTB->SetBinError(binX, data.POLY_TEMPSENS_BOTTOM * REL_ERROR);
                        hSLDOAna->SetBinContent(binX, data.TEMPSENS_ANA_SLDO);
                        hSLDOAna->SetBinError(binX, data.TEMPSENS_ANA_SLDO * REL_ERROR);
                        hSLDODig->SetBinContent(binX, data.TEMPSENS_DIG_SLDO);
                        hSLDODig->SetBinError(binX, data.TEMPSENS_DIG_SLDO * REL_ERROR);
                        hSLDOCen->SetBinContent(binX, data.TEMPSENS_CENTER);
                        hSLDOCen->SetBinError(binX, data.TEMPSENS_CENTER * REL_ERROR);

                        // ##########################################
                        // # Convert seconds from epoch to HH:MM:SS #
                        // ##########################################
                        if(start_time < 0) start_time = data.timestamp;

                        int elapsed_seconds = static_cast<int>(data.timestamp - start_time);
                        int hours           = elapsed_seconds / 3600;
                        int minutes         = (elapsed_seconds % 3600) / 60;
                        int seconds         = elapsed_seconds % 60;

                        char time_buffer[16];
                        snprintf(time_buffer, sizeof(time_buffer), "%02d:%02d:%02d", hours, minutes, seconds);
                        const std::string time_str(time_buffer);

                        hChipCurr->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hIAna->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hIDig->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hAnaShunt->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hDigShunt->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hVinAna->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hVDAna->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hVinDig->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hVDDig->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hIrf->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hNTCrel->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hNTCabs->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hPTT->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hPTB->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hSLDOAna->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hSLDODig->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                        hSLDOCen->GetXaxis()->SetBinLabel(binX, time_str.c_str());
                    }

                    const uint16_t start_bin = 1;
                    const uint16_t end_bin   = dataList.size();

                    hChipCurr->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hIAna->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hIDig->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hAnaShunt->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hDigShunt->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hVinAna->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hVDAna->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hVinDig->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hVDDig->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hIrf->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hNTCrel->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hNTCabs->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hPTT->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hPTB->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hSLDOAna->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hSLDODig->GetXaxis()->SetRangeUser(start_bin, end_bin);
                    hSLDOCen->GetXaxis()->SetRangeUser(start_bin, end_bin);
                }
}

void PowerTrimmingHistograms::process()
{
    for(auto& PreampCurr: PreamplifiersCurrent) drawChip<TH1F>(*PreampCurr);
    for(auto& CompCurr: ComparatorsCurrent) drawChip<TH1F>(*CompCurr);
    drawChip<TH1F>(LDACCurrent);

    drawChip<TH1F>(theChipCurrVsTimeContainer, "PE1");
    drawChip<TH1F>(theAnaInVsTimeContainer, "PE1");
    drawChip<TH1F>(theDigInVsTimeContainer, "PE1");
    drawChip<TH1F>(theAnaShuntVsTimeContainer, "PE1");
    drawChip<TH1F>(theDigShuntVsTimeContainer, "PE1");
    drawChip<TH1F>(theVINAVsTimeContainer, "PE1");
    drawChip<TH1F>(theVDDAVsTimeContainer, "PE1");
    drawChip<TH1F>(theVINDVsTimeContainer, "PE1");
    drawChip<TH1F>(theVDDDVsTimeContainer, "PE1");
    drawChip<TH1F>(theIrefVsTimeContainer, "PE1");
    drawChip<TH1F>(theInternalNTCRelContainer, "PE1");
    drawChip<TH1F>(theInternalNTCAbsContainer, "PE1");
    drawChip<TH1F>(thePolyTempSensTopContainer, "PE1");
    drawChip<TH1F>(thePolyTempSensBottomContainer, "PE1");
    drawChip<TH1F>(theTempsensAnaSldoContainer, "PE1");
    drawChip<TH1F>(theTempsensDigSldoContainer, "PE1");
    drawChip<TH1F>(theTempsensCenterContainer, "PE1");
}
