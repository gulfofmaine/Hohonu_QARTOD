from pydantic import BaseModel, Field

FEET_TO_METERS = 0.3048


class GrossRange(BaseModel):
    """Default values for gross range tests"""
    suspect_upper_limit: float | None = None
    suspect_lower_limit: float | None = None
    fail_upper_limit: float | None = None
    fail_lower_limit: float | None = None


class RateOfChange(BaseModel):
    """Default values for rate of change tests"""
    rate_threshold: float | None = None


class Spike(BaseModel):
    """Default values for spike tests"""
    suspect_threshold: float | None = None
    fail_threshold: float | None = None


class FlatLine(BaseModel):
    """Default values for flat line tests"""
    tolerance: float | None = None
    suspect_threshold: float | None = None
    fail_threshold: float | None = None


class DefaultValues(BaseModel):
    """Default values for QC tests"""

    gross_range: GrossRange = Field(default_factory=GrossRange)
    rate_of_change: RateOfChange = Field(default_factory=RateOfChange)
    spike: Spike = Field(default_factory=Spike)
    flat_line: FlatLine = Field(default_factory=FlatLine)
    


class Region:
    name: str
    attribution: str

    general_info: str

    gross_range_test_help: str
    rate_of_change_test_help: str
    spike_test_help: str
    flat_line_test_help: str

    def calculate_defaults(self, mllw: float, mhhw: float) -> DefaultValues:
        raise NotImplementedError("Needs to be implemented by an individual region")
    


class GulfOfMaine(Region):
    name = "Gulf of Maine"
    attribution = "Hannah Baranes, GMRI 2024"

    general_info = """
    Testing range suggestions developed in coordination with
    Hannah Baranes for the Gulf of Maine region.
    """

    gross_range_test_help = """
    ### Gross range test configuration for Gulf of Maine (not New England Shelf)

    #### Suspect Limits

    For stations with tidal datums (might not want this approach because it will always take a while to get tidal datums, and tidal datums change):  
    - Upper limit of range: MHHW + 6 ft  
    - Lower limit of range: MLLW – 4.5 ft  

    

    For stations without tidal datums:  
    - If there are no tidal datums because the station was just installed: use VDatum to get MHHW and MLLW relative to navd88_meters at a point close to the sensor, and use the same upper and lower limits   
        - Note: if it’s a station with river influence (like Bath), it might require some local expertise to set the limits. A solid approach is just taking the HW and LW measured over the course of the first week, and using something like HW + 10 ft and LW – 10 ft to be conservative  
    - If there are no tidal datums because the sensor bottoms out at low tide:  
        - Lower limit: Use the dry bottom elevation  
        - Upper limit: Use VDatum MHHW + 6 ft

                                
    #### Fail upper and lower limits
    - Upper limit: distance to water is less than whatever the minimum sensing range is  
    - Lower limit: either hard bottom (if it’s a site that bottoms out at LW, or if we have a depth measurement at the site), or distance to water = maximum of sensing range  
                
    #### Notes  

    Top recorded water levels, in ft MHHW (and year)  
    - Gulf of Maine 
        - Eastport: 5.07 (2020)  
        - Bar Harbor: 4.43 (2024) 
        - Portland: 4.67 (2024) 
        - Boston: 4.89 (2018) 
    - New England Shelf 
        - Chatham, MA: 4.28 (2014)  
        - Newport, RI: 9.45 (1938)
        -New London, CT: 7.53 (1938) 

    Lowest navd88_meters  
    - Eastport: -3.46 ft MLLW  (this will have the largest variability)  
    """

    rate_of_change_test_help = """
    ### Rate of change test. Input as a rate.  

    - Suspect: 0.75 feet per 6 minutes  
    - Fail: 1 foot per 6 minutes  

    Rationale: max rate of change from tides in Eastport is 5.3 ft per hour (midtide on 1/13/2024), or ~0.5 ft per 6 minutes. Add 0.25 feet for a sustained wind-driven increase in water level.  

    May want to adjust this so it’s dependent on tidal range  
    """

    spike_test_help = """
    ### Spike test: Input as a magnitude that’s checked across a measurement and the two adjacent measurements.  

    Maybe default to same as rate of change test? 
    """

    flat_line_test_help = """
    ### Flat line test: If there’s some lack of variance over some amount of time, mark as suspect/fail 

    Suspect/Fail = how long do subsequent values stay within that threshold before it’s considered flat? (input as a time) 

    For example, if all measurements over the past 4 hours are within 10 cm of each other, fail the flatline test (then tolerance = 10 cm, and time = 4 hours) 

    When a sensor flatlines, the system voltage and temperature sensor may still be causing variation 

    Let’s start with 0.1 feet over 2 hours for suspect, and 0.1 feet over 3 hours for fail.  


    Rationale: During neap tides in Portland, you could see as little as +/- 0.25 ft per hour of variation in the 2 hours around slack tide (HW or LW)  
    """

    def calculate_defaults(self, mllw: float, mhhw: float) -> DefaultValues:
        return DefaultValues(
            gross_range=GrossRange(
                suspect_upper_limit=mhhw + 6 * FEET_TO_METERS,
                suspect_lower_limit=mllw - 4.5 * FEET_TO_METERS,
                fail_upper_limit=mhhw + 6 * FEET_TO_METERS,
                fail_lower_limit=mllw - 4.5 * FEET_TO_METERS,
            ),
            rate_of_change=RateOfChange(
                rate_threshold=0.75 * FEET_TO_METERS
            ),
            spike=Spike(
                suspect_threshold=0.75 * FEET_TO_METERS,
                fail_threshold=1.5 * FEET_TO_METERS,
            ),
            flat_line=FlatLine(
                tolerance=0.1 * FEET_TO_METERS,
                suspect_threshold=2 * 60 * 60,
                fail_threshold=3 * 60 * 60,
            )
        )