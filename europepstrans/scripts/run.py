import argparse
import sys
import os

from europepstrans.model.pathway import TransformationPathway


def run_3_regions():

    dir_path = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)), os.pardir)
    )

    capacity_file = os.path.join(dir_path,
                                 'data',
                                 'europepstrans_initial_capacity.csv')
    model = TransformationPathway(initial_capacity=capacity_file)
    print(model.initial_capacity)

if __name__ == '__main__':
    # setup parser and define help text
    parser = argparse.ArgumentParser(
        description="Model - choose from list below" +
        """

        Available models
         * 3_regions
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # add arguments to be parsed
    parser.add_argument('model', type=str,
                        help='See list of model in help.')

    # print help if no arguments are provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # collect arguments
    args = parser.parse_args()

    # action based of input
    if args.model == '3_regions':
        run_3_regions()