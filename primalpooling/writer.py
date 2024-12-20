import argparse
import pathlib

from primalbedtools.bedfiles import BedLineParser
import pandas as pd


# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}


def cli():
    parser = argparse.ArgumentParser(
        description="Turn an bedfile and IDT spec sheet into a protocol"
    )
    parser.add_argument(
        "--bedfile",
        type=pathlib.Path,
        help="Path to the bedfile",
        required=True,
    )
    parser.add_argument(
        "--outpath",
        type=pathlib.Path,
        help="Path to the output protocol",
        required=True,
    )
    parser.add_argument(
        "--spec_sheet",
        type=pathlib.Path,
        help="Path to the primer spec sheet",
        required=True,
    )
    parser.add_argument(
        "--wanted_plate",
        type=str,
        help="The name of the plate to resuspend",
        required=True,
    )
    parser.add_argument(
        "--weight_to_ul",
        type=float,
        help="The weight to ul ratio",
        default=2,
    )
    args = parser.parse_args()
    write_protocol(
        bedfile=args.bedfile,
        outpath=args.outpath,
        spec_sheet=args.spec_sheet,
        wanted_plate=args.wanted_plate,
        weight_to_ul=args.weight_to_ul,
    )


def parse_location(location: str) -> str:
    """
    Parses A01 -> A1
    """
    return location[0] + str(int(location[1:]))


def write_protocol(
    bedfile: pathlib.Path,
    outpath: pathlib.Path,
    spec_sheet: pathlib.Path,
    wanted_plate: str,
    weight_to_ul: float = 2,
) -> None:
    """
    Parse the bedfile and the bedlines

    Assumptions:
    - The primers are all suspended to 100uM
    - The primers all have enough volume
    """
    metadata = {
        "protocolName": f"Resuspend plate: {wanted_plate}",
        "author": "Chris Kent. c.g.kent@bham.ac.uk",
        "description": "Resuspends primers according to primerWeight spec sheet",
    }

    # Read in the bedfile
    _headers, bedlines = BedLineParser.from_file(bedfile)

    # Load in the spec sheet
    spec_sheet_data = pd.read_excel(spec_sheet)

    # Get the wanted plate
    plate = spec_sheet_data[spec_sheet_data["Plate Name"] == wanted_plate]
    if plate.empty:
        raise ValueError(
            f"Plate ('{wanted_plate}') not found in spec sheet. Options are {spec_sheet_data['Plate Name'].unique()}"
        )

    # get the bedlines for the wanted plate
    wanted_bedlines = [
        line for line in bedlines if line.primername in plate["Sequence Name"].values
    ]

    # Parse the bedlines into a dataframe
    bedlines_df = pd.DataFrame(
        [
            {
                "Sequence Name": line.primername,
                "weight": line.weight if line.weight else 1,
                "volume": (line.weight if line.weight else 1) * weight_to_ul,
            }
            for line in wanted_bedlines
        ]
    )

    comb_data = pd.merge(plate, bedlines_df, on="Sequence Name", how="inner")

    # Parse the A01 -> A1
    comb_data.sort_values("Well Position", inplace=True)
    comb_data["Well Position"] = comb_data["Well Position"].apply(parse_location)

    # calculate the volume of the weights
    primer_weights = [x.weight if x.weight else 1 for x in wanted_bedlines]
    total_weight = sum(primer_weights)

    # Check the max weight is less than 20
    if comb_data["volume"].max() > 20:
        raise ValueError(
            f"Max primer volume is greater than 20ul ({comb_data[["volume"]].max()}ul)."
        )
    # Check the min weight is greater than 1
    if comb_data["volume"].min() < 1:
        raise ValueError(
            f"Min primer volume is less than 1ul ({comb_data[["volume"]].max()}ul)."
        )
    # Check the total volume is less than 1000
    if comb_data["volume"].sum() > 1000:
        raise ValueError(
            f"Total primer volume is greater than 1000ul ({total_weight}ul)."
        )

    with open(outpath, "w") as f:
        ## Write the metadata and requirements
        f.write("from opentrons import protocol_api\n\n")
        f.write(f"metadata = {metadata.__str__()}\n\n")
        f.write(f"requirements = {requirements.__str__()}\n\n")

        ## Write the run function
        f.write("def run(protocol: protocol_api.ProtocolContext):\n")
        # Write labware
        f.write(
            "\tinput_plate = protocol.load_labware('biorad_96_wellplate_200ul_pcr', location='4')\n"
        )
        f.write(
            "\ttiprack = protocol.load_labware('opentrons_96_tiprack_20ul', location='1')\n"
        )
        f.write(
            "\toutput_tube = protocol.load_labware('opentrons_24_aluminumblock_nest_1.5ml_screwcap', location='7')\n"
        )

        f.write(
            "\tleft_pipette = protocol.load_instrument('p300_multi_gen2', mount='left')\n"
        )
        f.write(
            "\tright_pipette = protocol.load_instrument('p20_single_gen2', mount='right')\n"
        )

        for i, row in comb_data.iterrows():
            # Pick up tip
            f.write(f"\tright_pipette.pick_up_tip(tiprack['{row['Well Position']}'])\n")
            f.write(
                f"\tright_pipette.aspirate({row['volume']}, input_plate['{row['Well Position']}'])\n"
            )
            f.write(f"\tright_pipette.dispense({row['volume']}, output_tube['A1'])\n")
            f.write("\tright_pipette.drop_tip()\n")


if __name__ == "__main__":
    write_protocol(
        bedfile=pathlib.Path(
            "/Users/kentcg/schemes/modjadji-tb/new-tb-scheme/primer.bed"
        ),
        outpath=pathlib.Path("test_output.py"),
        spec_sheet=pathlib.Path(
            "/Users/kentcg/Library/CloudStorage/OneDrive-UniversityofBirmingham/primer-stocks/modjadji-tb/Plate Specs.xlsx"
        ),
        wanted_plate="modjadji-tb_1.2",
    )
