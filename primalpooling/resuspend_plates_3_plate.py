from opentrons import protocol_api

# metadata
metadata = {
    "protocolName": "Resuspend 3 Plate",
    "author": "Chris Kent. c.g.kent@bham.ac.uk",
    "description": "Resuspend primers in TE buffer, then combine",
}

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    # labware
    input_plates = [
        protocol.load_labware("biorad_96_wellplate_200ul_pcr", location="4"),
        protocol.load_labware("biorad_96_wellplate_200ul_pcr", location="5"),
        protocol.load_labware("biorad_96_wellplate_200ul_pcr", location="6"),
    ]
    tipracks = [
        protocol.load_labware("opentrons_96_tiprack_300ul", location="1"),
        protocol.load_labware("opentrons_96_tiprack_300ul", location="2"),
        protocol.load_labware("opentrons_96_tiprack_300ul", location="3"),
    ]
    output_plate = [
        protocol.load_labware(
            "biorad_96_wellplate_200ul_pcr", location="7"
        ),  # Check this
        protocol.load_labware(
            "biorad_96_wellplate_200ul_pcr", location="8"
        ),  # Check this
        protocol.load_labware(
            "biorad_96_wellplate_200ul_pcr", location="9"
        ),  # Check this
    ]

    te = protocol.load_labware("axygen_1_reservoir_90ml", location="10")
    pool_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", location="11")

    # pipettes
    left_pipette = protocol.load_instrument(
        "p300_multi_gen2",
        mount="left",  # Check this
    )

    # commands

    # Resuspend
    for i, input_plate in enumerate(input_plates):
        # For each col resuspend
        for coli in range(12):
            col_id = "A" + str(coli + 1)
            left_pipette.pick_up_tip(tipracks[i][col_id])
            # Transfer 100ul from te to input_plate
            left_pipette.aspirate(100, te["A1"])
            left_pipette.dispense(100, input_plate[col_id])
            # Return tip to tiprack
            left_pipette.drop_tip(tipracks[i][col_id])

    # Mix and transfer
    for i, input_plate in enumerate(input_plates):
        pool_plate_id = "A" + str(i + 1)
        for coli in range(12):
            col_id = "A" + str(coli + 1)
            left_pipette.pick_up_tip(tipracks[i][col_id])
            left_pipette.mix(10, 50, input_plate[col_id])
            left_pipette.aspirate(30, input_plate[col_id])
            left_pipette.dispense(20, output_plate[i][col_id])
            left_pipette.dispense(10, pool_plate[pool_plate_id])

            left_pipette.drop_tip(
                tipracks[i][col_id],
            )
