"""
Unique prose descriptions for Switzerland's 4 hydropower reservoir regions.
Used on dam detail pages to provide SEO-friendly, human-readable context.

Swiss "dams" in this dashboard are aggregated regions as published by the
Swiss Federal Office of Energy (BFE / Bundesamt für Energie). Each region
encompasses dozens of individual reservoirs that collectively form the backbone
of Switzerland's Alpine hydropower network, which provides approximately 55%
of the country's electricity generation.
"""
from __future__ import annotations

CH_DAM_DESCRIPTIONS: dict[str, str] = {
    "Wallis": (
        "The Wallis region — known in French as Valais — is the hydropower capital of "
        "Switzerland and one of the most significant Alpine energy-producing territories "
        "in Europe. Occupying the upper Rhône valley between the Pennine Alps to the "
        "south and the Bernese Alps to the north, Wallis concentrates the highest "
        "density of major dams anywhere in the Alps. The canton alone accounts for "
        "roughly half of Switzerland's total hydropower storage capacity, which is "
        "approximately 4,300 GWh or around 3,655 hm³ when expressed as stored volume. "
        "The Grand Dixence dam, the tallest gravity dam in the world at 285 metres, "
        "stores water from 35 glaciers collected by an extraordinary network of "
        "underground tunnels stretching more than 100 kilometres through the mountain "
        "massif. The Lac des Dix, its reservoir, holds 401 million cubic metres at "
        "full supply level — making it the largest reservoir in Switzerland by volume. "
        "Other landmark structures include the Mauvoisin arch dam (250 m, one of the "
        "highest arch dams globally) impounding the Lac de Mauvoisin, and the Mattmark "
        "dam, an embankment dam holding the Mattmarksee at the head of the Saas valley. "
        "Glacier retreat is the central long-term concern for Wallis hydropower: as "
        "glaciers shrink they initially release more meltwater, temporarily boosting "
        "reservoir inflows, but the long-term trajectory is towards reduced summer "
        "flows. Swiss federal agencies monitor this transition carefully, and Wallis "
        "reservoirs are managed with increasing seasonal precision to balance immediate "
        "supply with multi-year resource sustainability. The Rhône river, originating "
        "from the Rhône Glacier at the Furka Pass, drains the region westward through "
        "Martigny before flowing into Lake Geneva."
    ),
    "Graubuenden": (
        "Graubünden — the largest Swiss canton by area and the only officially "
        "trilingual canton, using German, Romansh, and Italian — contains some of the "
        "most geographically diverse and hydropower-rich terrain in the Alps. The "
        "canton's hydropower reservoirs have a total storage capacity of approximately "
        "2,100 GWh (around 1,785 hm³), making Graubünden the second most important "
        "region in Switzerland after Wallis. The Rhine, Inn (En), and Adda river "
        "systems all have their headwaters in Graubünden, draining respectively to the "
        "North Sea, the Danube (via the Black Sea), and the Adriatic — the only point "
        "in Europe where three major continental drainage divides meet. The Albigna dam "
        "in the Bregaglia valley, an arch dam built into crystalline granite, and the "
        "Punt dal Gall (Livigno) dam on the Inn/En river — which also supplies the "
        "Italian side of the Reschensee complex — are among the signature structures. "
        "The Lago di Lei, shared with Italy, is fed by the Valle di Lei and operated "
        "jointly by Swiss and Italian utilities, an example of the transboundary "
        "hydropower cooperation that characterises Alpine energy management. Graubünden "
        "receives substantial snowfall in winter across its high passes — including the "
        "famous Engadine valley around St Moritz — and snowmelt dominates reservoir "
        "refill in May and June each year. Engadine's Inn valley contributes flow to "
        "the Austrian Inn and ultimately the Danube, giving Graubünden an unusually "
        "large hydrological footprint for a landlocked Alpine canton. Major operators "
        "include Kraftwerke Hinterrhein (KHR), Engadiner Kraftwerke, and Repower."
    ),
    "Tessin": (
        "Tessin — Ticino in Italian, the sole officially Italian-speaking canton of "
        "Switzerland — occupies the southern slopes of the Alps, draining southward "
        "into the Po basin and the Adriatic rather than northward like most Swiss "
        "cantons. This distinctive south-facing geography means Tessin's climate is "
        "markedly Mediterranean in character, with warm summers, mild winters at lower "
        "elevations, and intense autumn rainfall events that can fill reservoirs rapidly. "
        "The canton's hydropower storage capacity is approximately 1,200 GWh (around "
        "1,020 hm³), concentrated in the Ticino, Maggia, and Verzasca river systems. "
        "The Verzasca dam (Contra dam) at 220 metres is perhaps Switzerland's most "
        "internationally recognised structure — achieving global fame after serving as "
        "the location for the James Bond bungee jump sequence in GoldenEye (1995). "
        "The Lago del Sambuco, the Lago della Luzzone (site of one of the slimmest arch "
        "dams in the world, with a crest length-to-height ratio of 3.7:1), and the Lago "
        "di Vogorno (Verzasca reservoir) are among the principal storage bodies. Autumn "
        "flooding is a recurrent feature in Tessin due to southerly atmospheric flow "
        "events that deposit heavy rainfall on the southern Alpine face, and reservoir "
        "operators must balance flood control with energy storage objectives during "
        "these episodes. Aziende Industriali di Lugano (AIL) and Officine Idroelettriche "
        "della Maggia (OFIMA) are among the principal power producers in the canton. "
        "The Ticino river eventually feeds Lake Maggiore, shared with the Italian "
        "region of Piedmont, before reaching the Po delta."
    ),
    "UebrigCH": (
        "The UebrigCH (Rest of Switzerland) category aggregates hydropower reservoir "
        "storage from all Swiss cantons not separately classified as Wallis, Graubünden, "
        "or Tessin. This includes the central and northern Alpine cantons of Uri, "
        "Bern, Glarus, Schwyz, Nidwalden, and Obwalden, as well as smaller contributions "
        "from Fribourg, Vaud, and the Bernese Oberland. The combined storage capacity "
        "is approximately 1,300 GWh (around 1,105 hm³). The most significant "
        "hydropower complexes in this aggregated region are the Grimsel system in the "
        "Bernese Alps — comprising the Grimselsee (KWO Kraftwerke Oberhasli), Räterichsbodensee, "
        "and Oberaarsee — which collectively form one of the most sophisticated "
        "pump-storage systems in Switzerland. The Grimselsee reservoir at 1,908 metres "
        "altitude is capable of pumping water uphill to the Oberaarsee during periods "
        "of surplus grid electricity (from wind or solar), then generating on demand "
        "during peak price periods. The Linthal 2015 expansion project in the canton "
        "of Glarus added 1,000 MW of pump-storage capacity through the underground "
        "Muttsee cavern scheme, making it one of the largest such projects in Europe. "
        "The Sustenpass, Susten, and Reuss river catchments feed into this region's "
        "storage network. The Aare river — Switzerland's longest entirely domestic "
        "river — originates in the Bernese Oberland from the Aare Glacier and flows "
        "through the Grimsel, Brienz, and Thun lakes before reaching Bern and "
        "eventually the Rhine. Alpiq and Axpo are among the dominant operators across "
        "the cantons in this aggregated category."
    ),
}


def get_ch_dam_description(name_en: str) -> str:
    """Return the prose description for a Swiss reservoir region, or a generic fallback."""
    return CH_DAM_DESCRIPTIONS.get(
        name_en,
        f"{name_en} is a Swiss hydropower reservoir region monitored by the Swiss "
        f"Federal Office of Energy (BFE / Bundesamt für Energie). Reservoir fill data "
        f"is published weekly as an aggregate across all hydropower reservoirs in the "
        f"region.",
    )
