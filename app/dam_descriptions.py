"""
Unique prose descriptions for each of the 17 major Cyprus dams.
Used on dam detail pages to provide SEO-friendly, human-readable context.
"""
from __future__ import annotations

DAM_DESCRIPTIONS: dict[str, str] = {
    "Kouris": (
        "Kouris is the largest dam in Cyprus, located in the Limassol district on the "
        "Kouris River. Completed in 1988, its 115 MCM capacity makes it the backbone of "
        "the island's water supply, serving the greater Limassol area and contributing to "
        "the Southern Conveyor network. The earth-fill dam stands 110 metres tall amid the "
        "Troodos foothills. Its reservoir levels are widely regarded as a barometer for the "
        "island's overall water security — when Kouris runs low, Cyprus feels the pressure."
    ),
    "Asprokremmos": (
        "Asprokremmos is the second-largest dam in Cyprus, situated in the Paphos district "
        "on the Xeros River. Built in 1982 with a capacity of 52 MCM, it supplies drinking "
        "water to the Paphos region and feeds the extensive irrigation network of the "
        "surrounding agricultural lowlands. The earth-fill structure rises 53 metres above "
        "the riverbed. Asprokremmos plays a critical role in western Cyprus water management "
        "and is a key indicator of drought severity in the Paphos catchment area."
    ),
    "Evretou": (
        "Evretou dam is located in the Paphos district on the Stavros tis Psokas River. "
        "Completed in 1986 with a capacity of 24 MCM, it serves as a vital source for "
        "irrigation across the fertile Chrysochou valley and parts of the Paphos coastline. "
        "The 72-metre earth-fill dam is nestled in the western Troodos foothills, surrounded "
        "by pine forest. Evretou's catchment receives some of the highest rainfall on the "
        "island, making it one of the more resilient reservoirs during moderate droughts."
    ),
    "Kannaviou": (
        "Kannaviou is a modern roller-compacted concrete dam in the Paphos district, "
        "completed in 2005 on the Ezousa River. With a capacity of 17.2 MCM, it is one of "
        "the newest additions to the Cyprus water infrastructure. The 75-metre dam supports "
        "both drinking water supply and irrigation for the Paphos lowlands. Its relatively "
        "recent construction means it benefits from modern engineering standards and "
        "monitoring systems, and it plays a growing role in the western water network."
    ),
    "Arminou": (
        "Arminou dam straddles the border of the Paphos and Limassol districts on the "
        "Diarizos River. Completed in 1998 with a capacity of 4.3 MCM, it is a smaller "
        "but strategically important reservoir that supplements supply to the Southern "
        "Conveyor system. The 42-metre dam sits in a steep, narrow gorge surrounded by "
        "the Troodos mountains, giving it a dramatic setting but a relatively small "
        "catchment area compared to its larger neighbours."
    ),
    "Germasoyeia": (
        "Germasoyeia dam is located just north of Limassol city on the Germasoyeia River, "
        "making it the closest major reservoir to an urban centre in Cyprus. Built in 1968 "
        "with a capacity of 13.5 MCM, it was one of the first modern dams on the island. "
        "The 48-metre earth-fill structure supplies part of Limassol's drinking water. Its "
        "proximity to the city and the popular river valley walking trails make it one of "
        "the most visited dam sites in Cyprus."
    ),
    "Kalavasos": (
        "Kalavasos dam lies in the Larnaca district on the Vasilikos River. Completed in "
        "1985 with a capacity of 17.1 MCM, it serves the Vasilikos industrial zone, local "
        "agriculture, and supplements Larnaca's water supply via the Southern Conveyor. "
        "The 60-metre earth-fill dam sits in the gently rolling countryside between the "
        "Troodos foothills and the southern coast. The area around the reservoir is rich "
        "in archaeological sites, including the Neolithic settlement of Kalavasos-Tenta."
    ),
    "Lefkara": (
        "Lefkara dam is situated in the Larnaca district on the Pentaschoinos River, near "
        "the famous lace-making village of Lefkara. Built in 1981 with a capacity of "
        "13.9 MCM, it provides water for irrigation and contributes to the regional supply "
        "network. The 68-metre earth-fill dam commands views of the dramatic limestone "
        "landscape typical of the area. Its reservoir levels closely track the rainfall "
        "patterns of the central Troodos rain shadow zone."
    ),
    "Dipotamos": (
        "Dipotamos dam is located in the Larnaca district on the Pentaschoinos River, "
        "upstream of Lefkara dam. Completed in 1986 with a capacity of 15.5 MCM, it works "
        "in tandem with Lefkara to manage the Pentaschoinos catchment. The 60-metre "
        "earth-fill structure sits in a remote valley of the eastern Troodos foothills. "
        "Dipotamos primarily supports agricultural irrigation in the surrounding region "
        "and acts as a buffer during heavy winter rainfall events."
    ),
    "Achna": (
        "Achna dam is located in the Famagusta district, close to the south-eastern coast "
        "of Cyprus. Unlike most Cypriot dams that impound river water, Achna functions "
        "primarily as a storage reservoir for treated wastewater and desalinated water, "
        "with a capacity of 6.8 MCM. Built in 1987, the 15-metre earth-fill structure "
        "supports the intensive agriculture of the Kokkinochoria red-soil region. Its role "
        "in wastewater reuse makes it increasingly important for sustainable water management."
    ),
    "Polemidia": (
        "Polemidia dam lies on the outskirts of Limassol, making it one of the most "
        "centrally located reservoirs in Cyprus. Completed in 1965 with a capacity of "
        "3.4 MCM, it is one of the oldest modern dams on the island. The 35-metre "
        "earth-fill dam on the Garyllis River originally supplied Limassol's drinking "
        "water, though today it primarily supports irrigation. The surrounding area has "
        "become increasingly urbanised, and the reservoir serves as a green corridor "
        "within the expanding Limassol metropolitan area."
    ),
    "Mavrokolympos": (
        "Mavrokolympos dam is situated in the Paphos district near the village of "
        "Kissonerga. Completed in 1966 with a capacity of 2.1 MCM, it is one of the "
        "smaller dams in the national network. The 30-metre earth-fill structure "
        "captures runoff from the western Troodos slopes and supports local "
        "agriculture, particularly the banana and citrus plantations of the "
        "coastal Paphos lowlands. Despite its modest size, Mavrokolympos is a "
        "useful indicator of rainfall patterns in the drier western catchments."
    ),
    "Argaka": (
        "Argaka dam is located in the Paphos district on the northern slopes of the "
        "Troodos mountains, near the village of Argaka on the Chrysochou Bay coast. "
        "Built in 1964 with a capacity of 0.99 MCM, it is one of the smallest dams "
        "in the national network. The compact earth-fill structure captures seasonal "
        "runoff to support local citrus and olive cultivation. Argaka's small catchment "
        "means it responds quickly to rainfall events but also dries out faster during "
        "extended dry spells."
    ),
    "Pomos": (
        "Pomos dam sits on the north-western coast of Cyprus in the Paphos district, "
        "near the fishing village of Pomos. Completed in 1967 with a capacity of "
        "0.86 MCM, it is among the smallest reservoirs in the national system. "
        "The earth-fill dam captures runoff from the steep north-facing Troodos "
        "slopes and supports local agriculture along the narrow coastal strip. "
        "The area around Pomos is one of the least developed stretches of the "
        "Cyprus coastline, adding ecological value to the reservoir's surroundings."
    ),
    "Vyzakia": (
        "Vyzakia dam is located in the Nicosia district, on the Serrachis River in "
        "the Morphou plain. Built in 1984 with a capacity of 1.7 MCM, it primarily "
        "serves agricultural irrigation in the citrus-growing region west of Nicosia. "
        "The 22-metre earth-fill structure sits in the flat lowlands north of the "
        "Troodos massif. Vyzakia's small capacity means it fills and drains relatively "
        "quickly, making it a sensitive indicator of seasonal rainfall patterns in "
        "the Mesaoria plain catchment."
    ),
    "Xyliatos": (
        "Xyliatos dam is located in the Nicosia district, in the heart of the "
        "Troodos mountains near the village of Xyliatos. Completed in 1982 with "
        "a capacity of 1.4 MCM, it is a small but scenically situated reservoir "
        "surrounded by dense pine forest. The 21-metre earth-fill dam captures "
        "runoff from the northern Troodos slopes and supports local agriculture. "
        "The Xyliatos area is popular with hikers, and the reservoir adds to the "
        "landscape value of this mountainous region."
    ),
    "Kalopanagiotis": (
        "Kalopanagiotis dam is nestled in the Nicosia district in the Marathasa "
        "valley, one of the most picturesque areas of the Troodos mountains. Built "
        "in 1967 with a capacity of 0.36 MCM, it is the smallest dam in the national "
        "network. The compact earth-fill structure captures water from the Setrachos "
        "River and supports the cherry and walnut orchards that the Marathasa valley "
        "is famous for. Despite its tiny capacity, it holds cultural significance as "
        "part of the water heritage of this UNESCO-listed mountain region."
    ),
}


def get_dam_description(name_en: str) -> str:
    """Return the prose description for a dam, or empty string if not found."""
    return DAM_DESCRIPTIONS.get(name_en, "")
