"""
Unique prose descriptions for Norway's 5 hydropower reservoir zones.
Used on dam detail pages to provide SEO-friendly, human-readable context.

Norwegian "dams" in this dashboard are aggregated electricity price zones
(NO1–NO5) as published by the Norwegian Water Resources and Energy Directorate
(NVE). Each zone encompasses hundreds of individual reservoirs that collectively
feed Norway's extensive hydropower network.
"""
from __future__ import annotations

NO_DAM_DESCRIPTIONS: dict[str, str] = {
    "NO1-East": (
        "The NO1 East electricity zone covers Eastern Norway, including Oslo, Akershus, "
        "Hedmark, Oppland, and the surrounding counties that drain into the Glomma and "
        "Drammen river systems. This zone is the most populous region of Norway and "
        "accounts for a significant share of national electricity consumption. The "
        "hydropower reservoirs here are fed primarily by snowmelt from the Jotunheimen "
        "and Rondane mountain ranges, with the melt season running from April through "
        "June providing the largest annual inflows. The Glomma, Norway's longest river, "
        "originates in the mountains of Innlandet and flows southward through a series "
        "of regulated lakes and power stations before reaching the Oslofjord. Key "
        "reservoirs in the zone include Mjøsa, Norway's largest lake, which provides "
        "both drinking water for several hundred thousand people and a substantial "
        "contribution to hydropower generation. The NO1 zone has a total hydropower "
        "storage capacity of approximately 11.2 TWh and is closely integrated with "
        "transmission links to Sweden, making it the most commercially active "
        "electricity trading zone in Norway. Reservoir levels in NO1 follow a "
        "predictable seasonal pattern: lowest in late winter before snowmelt begins, "
        "peaking in midsummer, and drawn down steadily through the autumn and winter "
        "heating season. The zone is operated by a combination of Statkraft, Eidsiva "
        "Energi, and other regional utilities."
    ),
    "NO2-Southwest": (
        "The NO2 Southwest zone encompasses Agder and parts of Rogaland in southwestern "
        "Norway, a region historically known as the cradle of Norwegian hydropower. This "
        "zone contains some of the largest and most strategically important reservoir "
        "systems in the country, including the Otra, Ulla-Førre, and Tokke-Vinje "
        "complexes. With a storage capacity of approximately 33.5 TWh, NO2 is by far "
        "the largest single reservoir zone in Norway, holding more water than any other "
        "Nordic country's entire hydropower system. The Blåsjø reservoir, the largest "
        "artificial lake in Norway covering over 82 square kilometres at full supply "
        "level, is the centrepiece of the Ulla-Førre development and a critical "
        "seasonal storage buffer for the entire Norwegian power system. The landscape "
        "of NO2 is defined by the dramatic mountains of the Setesdal highlands and the "
        "Hardangervidda plateau, where precipitation is among the highest in northern "
        "Europe — Vest-Agder receives up to 3,000 mm of rain annually on the western "
        "slopes. This makes NO2 the primary balancing reservoir for the Nordic power "
        "market, able to absorb surplus wind and solar energy in wet periods and "
        "release stored energy during dry spells or cold snaps. Statkraft, as the "
        "majority owner of Ulla-Førre, manages these reservoirs as part of a portfolio "
        "that extends across the entire Nordic market."
    ),
    "NO3-Central": (
        "The NO3 Central zone covers Trøndelag and parts of Møre og Romsdal in "
        "central Norway, centred on the city of Trondheim, the historical capital of "
        "Norway. The hydropower reservoirs in this zone are fed by the rivers draining "
        "the central mountain ranges including the Dovrefjell, Trollheimen, and "
        "Trollfjella massifs. The Orkla, Nea, and Surna river systems form the backbone "
        "of the NO3 hydropower network, with storage capacity of approximately 10.1 TWh. "
        "Central Norway's reservoirs are particularly important for local electricity "
        "supply since the region has historically had limited high-voltage transmission "
        "capacity southward. The Nedre Røssåga and Svartisen schemes in adjacent areas "
        "provide significant flexibility. The NO3 zone includes the Innerdalen reservoir "
        "valley, considered one of the most scenic glacier-carved landscapes in Norway. "
        "Snowpack in the high fells of Trøndelag typically persists until early June, "
        "and reservoir refill from snowmelt is a critical seasonal event for the zone's "
        "energy balance. The zone is also significant for offshore oil and gas industry "
        "supply, with energy-intensive petrochemical facilities on the Trøndelag coast "
        "requiring reliable baseload supply. TrønderEnergi and Statkraft are among the "
        "principal operators. The NO3 zone typically operates close to its storage "
        "capacity in autumn following a good summer melt season."
    ),
    "NO4-North": (
        "The NO4 North zone covers Nordland, Troms, and Finnmark — the vast Arctic and "
        "sub-Arctic region stretching from the Arctic Circle northward to Norway's "
        "border with Russia and Finland, encompassing nearly half of Norway's total "
        "land area. This zone is home to some of the most spectacular fjord and mountain "
        "landscapes in the world, and its hydropower resources are fed by both snowmelt "
        "and glacial runoff from the massive Svartisen glacier system, the second largest "
        "glacier complex in mainland Europe. The Alta, Sørfjord, Rana, and Ofoten "
        "complexes are among the largest schemes in the zone, which has a total storage "
        "capacity of approximately 18.3 TWh. Northern Norway's electricity production "
        "significantly exceeds its domestic consumption, making it a major net exporter "
        "to southern Norway and to Sweden via the Nordlink and other interconnectors. "
        "The NO4 zone experiences extreme seasonal variation in daylight — from polar "
        "night in winter to midnight sun in summer — which shapes both electricity "
        "demand and the timing of reservoir inflows. Statkraft's Svartisen scheme alone "
        "has an installed capacity of 350 MW, utilising glacial meltwater tunnelled "
        "directly from the glacier to underground turbines. The Sámi reindeer herding "
        "communities of Finnmark depend on catchment areas that overlap with reservoir "
        "management zones, and Norway's environmental legislation requires sensitive "
        "balancing of hydropower operation with indigenous land rights."
    ),
    "NO5-West": (
        "The NO5 West zone covers Vestland county, the coastal region centred on Bergen "
        "that is synonymous with Norway's fjord landscape and some of the world's most "
        "productive hydropower geography. This zone receives the highest annual "
        "precipitation in Europe — certain inland valleys record over 5,000 mm per year "
        "— making it a virtually inexhaustible source of runoff for reservoir filling. "
        "The Sira-Kvina, Lyse, BKK, and Statkraft Vestland schemes are among the most "
        "powerful and economically significant in Norway, collectively contributing "
        "a substantial share of Norway's total electricity output. The Jøsenfjord and "
        "Lysefjord systems in Rogaland, including the famous Preikestolen plateau "
        "overlooking the Lysefjord, are underlain by a vast network of tunnels and "
        "underground caverns carved for the Lyse Energi hydropower scheme. Storage "
        "capacity in NO5 is approximately 14.8 TWh. The zone's reservoirs are the "
        "first to receive Atlantic weather systems sweeping in from the North Sea, "
        "and in wet autumns they fill rapidly — occasionally spilling. Hardangerfjord, "
        "the second-longest fjord in the world, drains the eastern reaches of the zone "
        "via the Opo and Bjoreio rivers. The NO5 zone is directly connected to the "
        "NordLink submarine cable to Germany and the North Sea Link to the United "
        "Kingdom, making its reservoir levels a significant factor in pan-European "
        "electricity prices. Fjordkraft, Lyse Energi, and BKK are among the principal "
        "utility operators in the zone."
    ),
}


def get_no_dam_description(name_en: str) -> str:
    """Return the prose description for a Norwegian reservoir zone, or a generic fallback."""
    return NO_DAM_DESCRIPTIONS.get(
        name_en,
        f"{name_en} is a Norwegian electricity price zone monitored by the Norwegian "
        f"Water Resources and Energy Directorate (NVE). Reservoir fill data is "
        f"published weekly as an aggregate across all hydropower reservoirs in the zone.",
    )
