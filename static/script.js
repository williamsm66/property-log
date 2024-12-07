let propertyModal;

document.addEventListener('DOMContentLoaded', function() {
    propertyModal = new bootstrap.Modal(document.getElementById('propertyModal'));
    
    // Add event listeners for automatic calculations
    document.getElementById('purchasePrice').addEventListener('input', updateCalculations);
    document.getElementById('rooms').addEventListener('input', updateCalculations);
    document.getElementById('mortgageLtv').addEventListener('input', updateCalculations);
    document.getElementById('mortgageRate').addEventListener('input', updateCalculations);
    document.getElementById('monthlyRent').addEventListener('input', updateCalculations);
    document.getElementById('renovationCost').addEventListener('input', updateCalculations);
    document.getElementById('brokerFeePercentage').addEventListener('input', updateCalculations);
    document.getElementById('buyersFeePercentage').addEventListener('input', updateCalculations);

    const propertyForm = document.getElementById('propertyForm');
    const resultsCard = document.getElementById('resultsCard');
    const calculatedResults = document.getElementById('calculatedResults');
    const propertyList = document.getElementById('propertyList');

    // Load existing properties
    loadProperties();

    // Handle form submission
    document.getElementById('propertyForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = {
            rightmove_url: document.getElementById('rightmoveUrl').value,
            address: document.getElementById('address').value,
            town: document.getElementById('town').value,
            status: document.getElementById('status').value,
            purchase_price: parseFloat(document.getElementById('purchasePrice').value),
            monthly_rent: parseFloat(document.getElementById('monthlyRent').value),
            renovation_cost: parseFloat(document.getElementById('renovationCost').value),
            valuation_after_renovation: parseFloat(document.getElementById('valuationAfterRenovation').value),
            mortgage_ltv: parseFloat(document.getElementById('mortgageLtv').value),
            mortgage_rate: parseFloat(document.getElementById('mortgageRate').value),
            mortgage_term_years: parseInt(document.getElementById('mortgageTermYears').value),
            mortgage_amount: parseFloat(document.getElementById('mortgageAmount').value),
            stamp_duty: parseFloat(document.getElementById('stampDuty').value),
            legal_fees: parseFloat(document.getElementById('legalFees').value),
            survey_cost: parseFloat(document.getElementById('surveyCost').value),
            broker_fee_percentage: parseFloat(document.getElementById('brokerFeePercentage').value),
            rooms: parseInt(document.getElementById('rooms').value),
            buyers_fee_percentage: parseFloat(document.getElementById('buyersFeePercentage').value)
        };

        try {
            const response = await fetch('/api/properties', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                propertyModal.hide();
                e.target.reset();
                loadProperties(); // Refresh the property list
            } else {
                const errorData = await response.json();
                console.error('Failed to save property:', errorData);
                alert('Failed to save property. Please check the console for details.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while saving the property.');
        }
    });

    function displayCalculatedResults(data) {
        // Show the results card
        resultsCard.style.display = 'block';

        // Create the results HTML
        calculatedResults.innerHTML = `
            <div class="col-md-4 mb-3">
                <h6>Rental Income</h6>
                <p>Monthly Rent: ${formatCurrency(data.monthly_rent)}</p>
                <p>Annual Rent: ${formatCurrency(data.annual_rent)}</p>
            </div>
            <div class="col-md-4 mb-3">
                <h6>Purchase Costs</h6>
                <p>Renovation Cost: ${formatCurrency(data.renovation_cost)}</p>
                <p>Stamp Duty: ${formatCurrency(data.stamp_duty)}</p>
                <p>Total Purchase Fees: ${formatCurrency(data.total_purchase_fees)}</p>
                <p>Total Money Needed: ${formatCurrency(data.total_money_needed)}</p>
            </div>
            <div class="col-md-4 mb-3">
                <h6>Mortgage Details</h6>
                <p>Mortgage Amount: ${formatCurrency(data.mortgage_amount)}</p>
                <p>Monthly Interest: ${formatCurrency(data.monthly_interest)}</p>
                <p>Annual Interest: ${formatCurrency(data.annual_interest)}</p>
            </div>
            <div class="col-md-4 mb-3">
                <h6>Running Costs</h6>
                <p>Maintenance: ${formatCurrency(data.maintenance)}</p>
                <p>Utility Bills: ${formatCurrency(data.utility_bills)}</p>
            </div>
        `;
    }

    async function loadProperties() {
        try {
            const response = await fetch('/api/properties');
            const properties = await response.json();
            
            propertyList.innerHTML = ''; // Clear existing list
            
            properties.forEach(property => {
                const propertyCard = createPropertyCard(property);
                propertyList.appendChild(propertyCard);
            });
        } catch (error) {
            console.error('Error loading properties:', error);
        }
    }

    function createPropertyCard(property) {
        const col = document.createElement('div');
        col.className = 'col-md-6 mb-4';
        
        col.innerHTML = `
            <div class="card h-100">
                <div class="card-body">
                    <h5 class="card-title">${property.address}</h5>
                    <h6 class="card-subtitle mb-2 text-muted">${property.town}</h6>
                    <p class="card-text">
                        <strong>Status:</strong> ${property.status}<br>
                        <strong>Rooms:</strong> ${property.rooms}<br>
                        <strong>Purchase Price:</strong> ${formatCurrency(property.purchase_price)}<br>
                        <strong>Monthly Rent:</strong> ${formatCurrency(property.monthly_rent)}<br>
                        <strong>Total Money Needed:</strong> ${formatCurrency(property.total_money_needed)}
                    </p>
                    ${property.rightmove_url ? `<a href="${property.rightmove_url}" target="_blank" class="btn btn-sm btn-outline-primary">View on Rightmove</a>` : ''}
                </div>
            </div>
        `;
        
        return col;
    }

    function formatCurrency(value) {
        return new Intl.NumberFormat('en-GB', {
            style: 'currency',
            currency: 'GBP'
        }).format(value);
    }

    function updateCalculations() {
        const purchasePrice = parseFloat(document.getElementById('purchasePrice').value) || 0;
        const mortgageLtv = parseFloat(document.getElementById('mortgageLtv').value) || 75;
        const mortgageRate = parseFloat(document.getElementById('mortgageRate').value) || 6.29;
        const rooms = parseInt(document.getElementById('rooms').value) || 0;
        const monthlyRent = parseFloat(document.getElementById('monthlyRent').value) || 0;
        const renovationCost = parseFloat(document.getElementById('renovationCost').value) || 0;
        const brokerFeePercentage = parseFloat(document.getElementById('brokerFeePercentage').value) || 1;
        const buyersFeePercentage = parseFloat(document.getElementById('buyersFeePercentage').value) || 4;

        // Calculate mortgage details
        const mortgageAmount = purchasePrice * (mortgageLtv / 100);
        const grossMortgage = mortgageAmount * (1 + brokerFeePercentage / 100);
        const monthlyInterest = (grossMortgage * (mortgageRate / 100)) / 12;
        const annualInterest = monthlyInterest * 12;

        // Calculate purchase costs
        const stampDuty = calculateStampDuty(purchasePrice);
        const legalFees = 2000;
        const surveyCost = 800;
        const totalPurchaseFees = stampDuty + (buyersFeePercentage / 100 * purchasePrice) + legalFees + surveyCost;
        const totalMoneyNeeded = totalPurchaseFees + purchasePrice;

        // Calculate running costs
        const annualRent = monthlyRent * 12;
        const maintenance = annualRent * 0.04;
        const utilityBills = rooms * 1147;

        // Update form fields
        document.getElementById('mortgageAmount').value = mortgageAmount.toFixed(2);
        document.getElementById('stampDuty').value = stampDuty.toFixed(2);

        // Display calculated results
        const calculatedResults = {
            monthly_rent: monthlyRent,
            annual_rent: annualRent,
            renovation_cost: renovationCost,
            stamp_duty: stampDuty,
            total_purchase_fees: totalPurchaseFees,
            total_money_needed: totalMoneyNeeded,
            mortgage_amount: mortgageAmount,
            monthly_interest: monthlyInterest,
            annual_interest: annualInterest,
            maintenance: maintenance,
            utility_bills: utilityBills
        };

        displayCalculatedResults(calculatedResults);
    }

    function openAddPropertyModal() {
        propertyModal.show();
        
        // Set default values
        document.getElementById('mortgageLtv').value = '75';
        document.getElementById('mortgageRate').value = '6.29';
        document.getElementById('mortgageTermYears').value = '25';
        document.getElementById('legalFees').value = '2000';
        document.getElementById('surveyCost').value = '800';
        document.getElementById('brokerFeePercentage').value = '1';
        document.getElementById('buyersFeePercentage').value = '4';
        
        // Clear other fields
        document.getElementById('rightmoveUrl').value = '';
        document.getElementById('address').value = '';
        document.getElementById('town').value = '';
        document.getElementById('purchasePrice').value = '';
        document.getElementById('monthlyRent').value = '';
        document.getElementById('renovationCost').value = '';
        document.getElementById('valuationAfterRenovation').value = '';
        document.getElementById('rooms').value = '';
        
        updateCalculations();
    }

    function calculateStampDuty(purchasePrice) {
        let stampDuty = 0;
        
        if (purchasePrice <= 250000) {
            stampDuty = purchasePrice * 0.03;
        } else if (purchasePrice <= 925000) {
            stampDuty = (250000 * 0.03) + ((purchasePrice - 250000) * 0.08);
        } else if (purchasePrice <= 1500000) {
            stampDuty = (250000 * 0.03) + (675000 * 0.08) + ((purchasePrice - 925000) * 0.13);
        } else {
            stampDuty = (250000 * 0.03) + (675000 * 0.08) + (575000 * 0.13) + ((purchasePrice - 1500000) * 0.15);
        }

        return Math.round(stampDuty);
    }
});

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-GB', {
        style: 'currency',
        currency: 'GBP'
    }).format(amount);
}

async function loadProperties() {
    try {
        const response = await fetch('/api/properties');
        const properties = await response.json();
        
        const propertyList = document.getElementById('propertyList');
        propertyList.innerHTML = '';
        
        properties.forEach(property => {
            const card = document.createElement('div');
            card.className = 'col-md-4 mb-4';
            card.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">${property.address}</h5>
                        <h6 class="card-subtitle mb-2 text-muted">${property.town}</h6>
                        <p class="card-text">
                            <strong>Purchase Price:</strong> ${formatCurrency(property.purchase_price)}<br>
                            <strong>Monthly Rent:</strong> ${formatCurrency(property.monthly_rent)}<br>
                            <strong>Rooms:</strong> ${property.rooms}<br>
                            <strong>Status:</strong> ${property.status}
                        </p>
                        <a href="${property.rightmove_url}" target="_blank" class="card-link">View on Rightmove</a>
                    </div>
                </div>
            `;
            propertyList.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading properties:', error);
    }
}

// Load properties when the page loads
loadProperties();
