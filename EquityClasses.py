import numpy as np
from datetime import datetime as dt, timedelta
from datetime import date
from enum import IntEnum
from dataclasses import dataclass
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any


class Frequency(IntEnum):
    ANNUAL = 1
    BIANNUAL = 2
    TRIANNUAL = 3
    QUARTERLY = 4
    MONTHLY = 12


@dataclass
class EquityShare:
    asset_id: int
    nace: str
    issuer: str
    buy_date: date
    dividend_yield: float
    frequency: Frequency
    market_price: float

    @property
    def dividend_amount(self) -> float:
        return self.dividend_yield # Probably needs to be removed

    def generate_dividend_dates(self, modelling_date: date, end_date: date ) -> date:
        """

        :type modelling_date: date
        """
        delta = relativedelta(months=(12 // self.frequency))
        this_date = self.buy_date - delta
        while this_date < end_date:  # Coupon payment dates
            this_date = this_date + delta
            if this_date < modelling_date: #Not interested in past payments
                continue
            if this_date <= end_date:
                yield this_date # ? What is the advantage of yield here?

class EquitySharePortfolio():
    def __init__(self, equity_share: dict[int,EquityShare] = None):
        """

        :type equity_share: dict[int,EquityShare]
        """
        self.equity_share = equity_share

    def IsEmpty(self)-> bool:
        if self.equity_share == None:
            return True
        if len(self.equity_share) == 0:
            return True
        return False

    def add(self,equity_share: EquityShare) :
        """

        :type equity_share: EquityShare
        """
        if self.equity_share == None:
            self.equity_share = {equity_share.asset_id: equity_share}
        else:
            self.equity_share.update({equity_share.asset_id: equity_share})



    def create_dividend_dates(self, modelling_date, end_date)->dict:
        """
                Create the vector of dates at which the dividends are paid out and the total amounts for
                all equity shares in the portfolio, for dates on or after the modelling date

                Parameters
                ----------
                self : EquitySharePortfolio class instance
                    The EquitySharePortfolio instance with populated initial portfolio.

                Returns
                -------
                EquityShare.coupondates
                    An array of datetimes, containing all the dates at which the coupons are paid out.

                """

        dividends: dict[date, float] = {}
        equity_share: EquityShare
        dividend_date: date
        for asset_id in self.equity_share:
            equity_share = self.equity_share[asset_id]
            dividend_amount = equity_share.dividend_amount
            for dividend_date in equity_share.generate_dividend_dates(modelling_date, end_date):
                if dividend_date in dividends:
                    dividends[dividend_date] = dividend_amount + dividends[dividend_date] # ? Why is here a plus? (you agregate coupon amounts if same date?)
                else:
                    dividends.update({dividend_date:dividend_amount})
        return dividends

## Create date fractions used in fast capitalizing and discounting
    def create_dividend_fractions(self, modelling_date)->dict:
        """
        Create the vector of year fractions at which the dividends are paid out and the total amounts for
        all equity shares in the portfolio, for dates on or after the modelling date

        Parameters
        ----------
        self : EquitySharePortfolio class instance
            The EquitySharePortfolio instance with populated initial portfolio.

        Returns
        -------
        EquityShare.dividendfrac
            An array of flats, containing all the date fractions at which the dividends are paid out.

        """        

        # other counting conventions MISSING

        n_equity = len(self.equity_share)  # Number of assets in the bond portfolio

        # Data structures list of lists for dividend payments
        alldatefrac = (
            []
        )  # this will save the date fractions of dividends for the portfolio
        alldatesconsidered = (
            []
        )  # this will save if a cash flow is already expired before the modelling date in the portfolio

        # Data structure list of lists for terminal amount repayment
        alldividenddatefrac = (
            []
        )  # this will save the date fractions of terminal value repayment for the portfolio
        alldividenddatesconsidered = (
            []
        )  # this will save if a bond is already expired before the modelling date in the portfolio

        for i_equity in range(0, n_equity):  # For each equity in the current portfolio
            # Reset objects for the next asset
            equitydatefrac = np.array(
                []
            )  # this will save date fractions of dividends of a single asset
            equitydatesconsidered = np.array(
                []
            )  # this will save the boolean, if the dividend date is after the modelling date

            equityterminaldatefrac = np.array(
                []
            ) # this will save date fractions of terminal sale of a single equity
            equityterminaldatesconsidered = np.array(
                []
            )  # this will save the boolean, if the maturity date is after the modelling date

            couponcounter = 0  # Counter of future coupon cash flows initialized to 0

            datenew = (
                self.dividend_dates[i_equity] - modelling_date
            )  # calculate the time difference between the coupondate and modelling date

            for onecoupondate in datenew:  # for each coupon date of the selected bond
                if onecoupondate.days > 0:  # coupon date is after the modelling date
                    equitydatefrac = np.append(
                        equitydatefrac, onecoupondate.days / 365.25
                    )  # append date fraction
                    equitydatesconsidered = np.append(
                        equitydatesconsidered, int(couponcounter)
                    )  # append "is after modelling date" flag
                couponcounter += 1
                # else skip
            alldatefrac.append(
                equitydatefrac
            )  # append what fraction of the date is each cash flow compared to the modelling date
            alldatesconsidered.append(
                equitydatesconsidered.astype(int)
            )  # append which cash flows are after the modelling date

            # Calculate if the maturity date is before the modelling date
            assetcalcnotionaldatefrac = (
                self.notionaldates[i_equity] - MD
            )  # calculate the time difference between the maturity date and modelling date

            if (
                assetcalcnotionaldatefrac[0].days > 0
            ):  # if maturity date is after modelling date
                equityterminaldatefrac = np.append(
                    equityterminaldatefrac, assetcalcnotionaldatefrac[0].days / 365.25
                )  # append date fraction
                equityterminaldatesconsidered = np.append(
                    equityterminaldatesconsidered, int(1)
                )  # append "is after modelling date" flag
            # else skip
            alldividenddatefrac.append(
                equityterminaldatefrac
            )  # append what fraction of the date is each cash flow compared to the modelling date
            alldividenddatesconsidered.append(
                equityterminaldatesconsidered.astype(int)
            )  # append which cash flows are after the modelling date

        # Save coupon related data structures into the object
        self.coupondatesfrac = alldatefrac
        self.datesconsidered = alldatesconsidered

        # Save notional amount related data structures into the object
        self.notionaldatesfrac = alldividenddatefrac
        self.datesconsiderednot = alldividenddatesconsidered

        return [
            alldatefrac,
            alldatesconsidered,
            alldividenddatefrac,
            alldividenddatesconsidered,
        ]  # return all generated data structures (for now)







# Calculate terminal value given growth rate, ultimate forward rate and vector of cash flows
    def equity_gordon(self,dividendyield, yieldrates, dividenddatefrac, ufr, g):

        num = np.power((1+g),dividenddatefrac)
        den = np.power((1+yieldrates),dividenddatefrac)
        termvalue = 1/((1+yieldrates[-1]) ** dividenddatefrac[-1]) * 1/(ufr-g)

        lhs = 1/dividendyield
        return np.sum(num/den)+termvalue-lhs 

## Bisection

    def bisection_spread(x_start, x_end, dividendyield, r_obs_est, dividenddatefrac, ufr, Precision, maxIter, growth_func):
        """
        Bisection root finding algorithm for finding the root of a function. The function here is the allowed difference between the ultimate forward rate and the extrapolated curve using Smith & Wilson.

        Args:
            cbPriced =  CorporateBondPriced object containing the list of priced bonds, spreads and cash flows
            xStart =    1 x 1 floating number representing the minimum allowed value of the convergence speed parameter alpha. Ex. alpha = 0.05
            xEnd =      1 x 1 floating number representing the maximum allowed value of the convergence speed parameter alpha. Ex. alpha = 0.8
            M_Obs =     n x 1 ndarray of maturities of bonds, that have rates provided in input (r). Ex. u = [[1], [3]]
            r_Obs =     n x 1 ndarray of rates, for which you wish to calibrate the algorithm. Each rate belongs to an observable Zero-Coupon Bond with a known maturity. Ex. r = [[0.0024], [0.0034]]
            ufr  =      1 x 1 floating number, representing the ultimate forward rate. Ex. ufr = 0.042
            Tau =       1 x 1 floating number representing the allowed difference between ufr and actual curve. Ex. Tau = 0.00001
            Precision = 1 x 1 floating number representing the precision of the calculation. Higher the precision, more accurate the estimation of the root
            maxIter =   1 x 1 positive integer representing the maximum number of iterations allowed. This is to prevent an infinite loop in case the method does not converge to a solution         
            approx_function
        Returns:
            1 x 1 floating number representing the optimal value of the parameter alpha 

        Example of use:
            >>> import numpy as np
            >>> from SWCalibrate import SWCalibrate as SWCalibrate
            >>> M_Obs = np.transpose(np.array([1, 2, 4, 5, 6, 7]))
            >>> r_Obs =  np.transpose(np.array([0.01, 0.02, 0.03, 0.032, 0.035, 0.04]))
            >>> xStart = 0.05
            >>> xEnd = 0.5
            >>> maxIter = 1000
            >>> alfa = 0.15
            >>> ufr = 0.042
            >>> Precision = 0.0000000001
            >>> Tau = 0.0001
            >>> BisectionAlpha(xStart, xEnd, M_Obs, r_Obs, ufr, Tau, Precision, maxIter)
            [Out] 0.11549789285636511

        For more information see https://www.eiopa.europa.eu/sites/default/files/risk_free_interest_rate/12092019-technical_documentation.pdf and https://en.wikipedia.org/wiki/Bisection_method
        
        Implemented by Gregor Fabjan from Qnity Consultants on 17/12/2021.
        """   

        yStart = growth_func(dividendyield, r_obs_est, dividenddatefrac, ufr, x_start)
        yEnd = growth_func(dividendyield, r_obs_est, dividenddatefrac, ufr, x_end)
        if np.abs(yStart) < Precision:
            return x_start
        if np.abs(yEnd) < Precision:
            return x_end # If final point already satisfies the conditions return end point
        iIter = 0
        while iIter <= maxIter:
            xMid = (x_end+x_start)/2 # calculate mid-point
            yMid = growth_func(dividendyield, r_obs_est, dividenddatefrac, ufr, xMid) # What is the solution at midpoint
            if ((yStart) == 0 or (x_end-x_start)/2 < Precision): # Solution found
                return xMid
            else: # Solution not found
                iIter += 1
                if np.sign(yMid) == np.sign(yStart): # If the start point and the middle point have the same sign, then the root must be in the second half of the interval   
                    x_start = xMid
                else: # If the start point and the middle point have a different sign than by mean value theorem the interval must contain at least one root
                    x_end = xMid
        return "Did not converge"


# Missing create cash flows





class Equity:
    def __init__(self, nace, issuedate, issuername, dividendyield, frequency, marketprice,terminalvalue,enddate):
        """
        Equity class saves 
        
        Properties
        ----------
        nace
        issuedate        
        frequency
        marketprice
        dividendyield
        terminalvalue
        growthrate
        dividenddates
        dividendfrac
        terminaldates
        dividendcfs
        terminalcfs        

        """
        self.nace = nace
        self.issuedate = issuedate
        self.issuername = issuername
        self.frequency = frequency
        self.marketprice = marketprice
        self.dividendyield = dividendyield
        self.terminalvalue = terminalvalue
        self.enddate = enddate
        self.terminaldates = []
        self.growthrate = []
        self.dividenddates = []
        self.dividendfrac = []
        self.terminaldates =[]
        self.dividendcfs = []
        self.terminalcfs = []

    def createcashflowdates(self):
        """
        Create the vector of dates at which the dividends and terminal value are paid out.

        Needs numpy as np and datetime as dt
        
        Parameters
        ----------
        self : CorporateBond class instance
            The CorporateBond instance with populated initial portfolio.

        Returns
        -------
        Equity.dividenddates
            An array of datetimes, containing all the dates at which the coupons are paid out.
        Equity.terminaldates
            An array of datetimes, containing the dates at which the principal is paid out
        """       

        nAssets = self.issuedate.size

        for iEquity in range(0,nAssets):
            issuedate = self.issuedate[iEquity]
            enddate   = self.enddate[iEquity]

            dates = np.array([])
            thisdate = issuedate

            while thisdate <= enddate:
                if self.frequency == 1:
                    thisdate = dt.date(thisdate.year + 1, thisdate.month, thisdate.day)
                    if thisdate <=enddate:
                        dates = np.append(dates,thisdate)
                    else:
                        #return dates
                        break
                elif self.frequency == 2:
                    thisdate = thisdate + dt.timedelta(days=182)
                    if thisdate <= enddate:
                        dates = np.append(dates, thisdate)
                    else:
                        break                

            self.dividenddates.append(dates)

            # Notional payoff date is equal to maturity
            self.terminaldates.append(np.array([self.enddate[iEquity]]))


class EquityPriced:
    def __init__(self, modellingdate,compounding, enddate, dividendyield, marketprice, terminalvalue, growthrates):
        """
        Equity class saves 
        
        Properties
        ----------
        modellingdate
        compounding
        enddate
        dividendyield
        growthrate
        marketprice
        terminalvalue
        bookprice
        dividenddatefrac
        terminaldatefrac
        dividendcfs
        terminalcfs
        """

        self.modellingdate = modellingdate
        self.compounding = compounding
        self.enddate = enddate
        self.dividendyield = dividendyield 
        self.growthrate = growthrates
        self.marketprice = marketprice 
        self.terminalvalue = terminalvalue
        self.bookprice = []
        self.dividenddatefrac = []
        self.terminaldatefrac =[]
        self.dividendcfs = []
        self.terminalcfs = []

  
    def createcashflows(self):
        """
        Convert information about the equity into a series of cash flows and a series of dates at which the cash flows are paid.

        Needs numpy as np
        Parameters
        ----------
        self : EquityPriced object
            

        Modifies
        -------
        EquityPriced
            ToDo.

        """       
        # Produce array of dates when coupons are paid out
       
        nAssets = self.marketprice.size
        
        # Missing what if date is 31,30
        # Missing other frequencies
        
        # Cash flow of each dividend
        #dividendsize = self.marketprice*self.dividendyield

        self.dividendcfs = []
        self.dividenddates = []
        self.terminaldates = []
        self.terminalcfs = []

        for iEquity in range(0,nAssets):
            startyear = self.issuedate[iEquity].year
            endyear   = self.maturitydate[iEquity].year
            month     = self.issuedate[iEquity].month
            day       = self.issuedate[iEquity].day
            
            coupondateone = np.array([])
            
            if self.frequency[iEquity] == 1:
                for selectedyear in range(startyear,endyear+1): # Creates array of dates for selected ZCB
                    dividenddateone = np.append(dividenddateone,dt.date(selectedyear,month,day))
            elif self.frequency[iEquity] == 2:
                #todo
                print("Not completed")
            else:
                #todo
                print("Not completed")
            
            self.dividendcfs.append(np.ones_like(dividenddateone)*dividendsize[iEquity])
            self.dividenddates.append(dividenddateone)

            # Terminal payoff date is equal to maturity
            self.terminaldates.append(np.array([self.maturitydate[iEquity]]))
       
            # Cash flow of the principal payback
            self.terminalcfs.append(np.array(self.terminal[iEquity]))


