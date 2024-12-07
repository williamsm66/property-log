/**
 * PropertyCalculator class
 * Contains all formulas from the Excel spreadsheet "Copy of Property Calculator Revised.xlsx"
 * These formulas are locked and should not be modified unless explicitly required
 */
class PropertyCalculator {
    constructor() {
        // Constants from Excel
        this.INSURANCE_COST = 300;
        this.UTILITY_COST_PER_ROOM = 1147;
        this.MAINTENANCE_RATE = 0.04;
    }

    /**
     * Calculate stamp duty based on purchase price
     * Excel formula: AE3
     */
    calculateStampDuty(purchasePrice) {
        if (purchasePrice <= 125000) {
            return purchasePrice * 0.05;
        } else if (purchasePrice <= 925000) {
            return (125000 * 0.05) + ((purchasePrice - 125000) * 0.08);
        } else if (purchasePrice <= 1500000) {
            return (125000 * 0.05) + (800000 * 0.08) + ((purchasePrice - 925000) * 0.13);
        } else {
            return (125000 * 0.05) + (800000 * 0.08) + (575000 * 0.13) + ((purchasePrice - 1500000) * 0.15);
        }
    }

    /**
     * Calculate total purchase fees
     * Excel formula: AF3 = AE3 + extra fees
     */
    calculateTotalPurchaseFees(stampDuty, extraFees = 0) {
        return stampDuty + extraFees;
    }

    /**
     * Calculate total money needed for purchase
     * Excel formula: AG3 = AF3 + I3
     */
    calculateTotalMoneyNeeded(totalPurchaseFees, purchasePrice) {
        return totalPurchaseFees + purchasePrice;
    }

    /**
     * Calculate bridging loan details
     * Excel formulas: AI3 through AW3
     */
    calculateBridgingLoan(params) {
        const {
            initialCash,
            totalMoneyNeeded,
            renovationCost,
            bridgingRate,
            arrangementRate,
            brokerRate,
            bridgingDuration
        } = params;

        const cashAfterPurchase = initialCash - totalMoneyNeeded;
        const bridgingNeeded = Math.max(0, renovationCost - cashAfterPurchase);
        const cashLeftoverAfterRenovations = Math.max(0, cashAfterPurchase - renovationCost);
        const arrangementFees = bridgingNeeded * arrangementRate;
        const totalBridging = bridgingNeeded + arrangementFees;
        const bridgingCost = totalBridging * bridgingRate * bridgingDuration;
        const totalGrossLoan = totalBridging + bridgingCost;
        const brokerFees = totalGrossLoan * brokerRate;
        const monthlyBridgingCost = bridgingCost / bridgingDuration;

        return {
            bridgingNeeded,
            cashLeftoverAfterRenovations,
            arrangementFees,
            totalBridging,
            bridgingCost,
            totalGrossLoan,
            brokerFees,
            monthlyBridgingCost,
            amountToRepay: totalGrossLoan
        };
    }

    /**
     * Calculate mortgage details
     * Excel formulas: AY3 through BD3
     */
    calculateMortgage(params) {
        const {
            mortgageLtv,  // Fixed parameter name
            valuationAfter,
            lenderFee,
            mortgageRate
        } = params;

        const mortgageAmount = (mortgageLtv * valuationAfter) + ((mortgageLtv * valuationAfter) * lenderFee);
        const mortgageFees = mortgageAmount * lenderFee;
        const annualMortgageInterest = (mortgageAmount + mortgageFees) * mortgageRate;

        return {
            mortgageAmount,
            mortgageFees,
            annualMortgageInterest
        };
    }

    /**
     * Calculate rental income and expenses
     * Excel formulas: BE3 through BK3
     */
    calculateRental(params) {
        const {
            monthlyRent,
            rooms,
            managementFee
        } = params;

        const annualRent = monthlyRent * 12;
        // Handle case where rooms is 0 or undefined
        const utilityBills = (rooms || 0) * this.UTILITY_COST_PER_ROOM;
        const maintenance = annualRent * this.MAINTENANCE_RATE;
        const managementFees = annualRent * managementFee;
        const totalRentalFees = managementFees + this.INSURANCE_COST + maintenance;
        const rentalIncome = annualRent - utilityBills - totalRentalFees;

        return {
            annualRent,
            utilityBills,
            maintenance,
            managementFees,
            totalRentalFees,
            rentalIncome
        };
    }

    /**
     * Calculate profit metrics
     * Excel formulas: R3 through V3
     */
    calculateProfit(params) {
        const {
            rentalIncome,           // BK3: gross annual rent
            annualMortgageInterest, // BC3: total interest
            totalMoneyNeeded,       // AG3: total money needed for purchase
            bridgingCost,          // AL3: Bridging loan cost
            renovationCost,        // N3: Cost of renovation
            arrangementFees,       // AR3: Total gross loan
            brokerFees,           // AT3: broker fees
            mortgageAmount,       // AY3: Amount to borrow
            valuationAfter       // M3: Evaluation for rental after work
        } = params;

        // BK3-BC3: gross annual rent minus total interest
        const annualProfit = rentalIncome - annualMortgageInterest;
        
        // AG3+AL3+N3+AR3+AT3-AY3: 
        // total money needed + bridging cost + renovation + total gross loan + broker fees - amount to borrow
        const cashLeftInDeal = totalMoneyNeeded + bridgingCost + renovationCost + 
                             arrangementFees + brokerFees - mortgageAmount;
        
        // R3*0.81: Annual profit times 0.81 (19% tax)
        const annualProfitAfterTax = annualProfit * 0.81;
        
        // R3/S3: Annual profit divided by cash left
        const totalROI = (annualProfit / cashLeftInDeal) * 100;
        
        // R3/M3: Annual profit divided by valuation after
        const totalYield = (annualProfit / valuationAfter) * 100;

        return {
            annualProfit,
            cashLeftInDeal,
            annualProfitAfterTax,
            totalROI,
            totalYield
        };
    }

    /**
     * Calculate flip profit
     * Excel formulas: W3 through Z3
     */
    calculateFlipProfit(params) {
        const {
            valuationAfter,
            totalMoneyNeeded,
            renovationCost,
            bridgingCost,
            arrangementFees,
            brokerFees
        } = params;

        const sellingFees = valuationAfter * 0.04;
        const flipProfitBeforeTax = valuationAfter - (totalMoneyNeeded + renovationCost + 
                                   bridgingCost + arrangementFees + brokerFees + sellingFees);
        const corporationTax = flipProfitBeforeTax * 0.19;
        const flipProfitAfterTax = flipProfitBeforeTax - corporationTax;

        return {
            flipProfitBeforeTax,
            corporationTax,
            flipProfitAfterTax
        };
    }
}
