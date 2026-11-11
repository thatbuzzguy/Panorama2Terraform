"""F8.9 the path 2 entry point: the run order, the arguments, and the exit codes
(`docs/API_CONVERSION_PATH.md` §6).

Four rules, stated once here.

1. The run order. The run reads the membership responses first, in the order
   `api_requests.membership_lists()` names them, then the entries `api_requests.scope_index()` names in index
   order. One response is read once: two lists can name one container, so a container named by two lists is read
   at the first place a list names it, and a container the run already read as a membership response is not read
   again for its index entry. `api_requests.py` states no read order and `provenance.py` rule 6 states no read
   rule for a path 2 run, so this is the only place the order is stated, and the record file the run wrote is
   the order's own statement
   (`tests/test_api_path.py::test_the_run_order_is_the_membership_lists_then_the_index_entries`).
2. The cross-response join is applied in run order, through the one join rule in `panorama_to_terraform.py`,
   which the run view takes as an argument. `api_requests.py` keeps no merge rule, so the four tables stay per
   response and the join is what makes one set for the run. The same content read as one whole-config export
   gives one fact, and read as two per-scope responses gives two.
3. The arguments are read through `panorama_to_terraform.shared_arguments`, and this entry point adds none of
   its own: the request set is the scope set, so there is no input file, no `--source`, no `--path`, and no
   `--parent`, because the parent walk stays inside one response (F8.5). The checks that apply to both entry
   points are read through `panorama_to_terraform.shared_checks`.
4. The exit codes. An argument error exits 2, a refused input exits 1 and writes no file, and the gate decides
   the run's exit code (F4.1). The gate gets the index this entry point built, so `request_set` reports as a
   rule that ran for a path 2 run, and the join findings print through the gate: this entry point prints no
   join block of its own.

The entry point states no rule an owner states: no naming rule, no writer, no console line, no container part,
no position part, no scope fact, no section fact, no unit rule, no join rule, no check, no report section, and
no block builder. It names no environment name of its own: it reads `source_fetch.API_KEY_ENV` through the door.
It calls `panorama_to_terraform.generate_run`, so the parse order and the emission order are stated once, and
neither entry point states a parse order of its own (criterion 3).

Usage:
    python3 api_to_terraform.py --host panorama.example.com --output-dir terraform_output
    # A run with an injected producer, so no request reaches the network:
    code = api_to_terraform.run(['--host', 'panorama.test', '--output-dir', out], producer=producer)
"""

import argparse
import sys

import api_requests
import entry_coverage
import panorama_to_terraform
import source_fetch
import state_input

# The name the README label prints for this entry point (criterion 9). It is data: `generate_readme` takes the
# name as an argument and states no path rule, so each entry point states only its own name.
ENTRY_POINT = 'api_to_terraform.py'


def build_parser() -> argparse.ArgumentParser:
    """The arguments one run reads (criterion 5), through the set `shared_arguments` states. The set names no
    source, so this entry point adds no argument of its own.
    """
    parser = argparse.ArgumentParser(
        description='Convert the Panorama API response set to Terraform configuration (path 2)'
    )
    panorama_to_terraform.shared_arguments(parser)
    return parser


def lists_read(parts) -> tuple:
    """The membership lists the run read, read back from the parts it built.

    The read set is the entry point's decision, so no list is stated here: a list counts when the run read the
    response for the container that holds it, read through `api_requests` for the path each list names.
    """
    return tuple(list_path for list_path in api_requests.membership_lists()
                 if any(part.request.path == api_requests.scope_path(api_requests.list_container(list_path))
                        for part in parts))


def read_part(args, path: str, producer=None):
    """One response, as the run holds it: the request that reads it, the source the door returned, and the
    parser built on that source (F8.5, so the line map and the parent walk are this response's only).
    """
    request = source_fetch.ApiRequest(host=args.host, path=path)
    source = source_fetch.fetch(request, args.cache_dir, producer=producer, offline=args.offline,
                                insecure=args.insecure, max_input_bytes=args.max_input_bytes)
    if source is None:
        # A producer that has no bytes for a request answers None, so the run order holds no part for it and
        # the join reports the index entry as a finding. No cache entry is written for bytes that never arrived.
        return None
    print(panorama_to_terraform.read_line(request))
    return panorama_to_terraform.part_for(source, request)


def run_order(args, producer=None) -> tuple:
    """The run order, and the only place that states it (rule 1): the membership responses first, then the
    entries the index names, in index order. Returns the parts and the index, because the index is built from
    the tables the run read.
    """
    parts = []
    for list_path in api_requests.membership_lists():
        path = api_requests.scope_path(api_requests.list_container(list_path))
        if any(part.request.path == path for part in parts):
            continue    # two lists can name one container, and one response is read once
        part = read_part(args, path, producer)
        if part is not None:
            parts.append(part)
    if not parts:
        # A run that read no response has no scope set to read and nothing to write, so it takes the refusal
        # shape: exit 1, and no file.
        raise ValueError(
            f"the run read no response from '{args.host}': the membership lists name no response, "
            "so no scope enters the index and the run has nothing to write."
        )

    # Rule 2: the four tables stay per response in `api_requests`, so the join is applied here, in run order,
    # through the one join rule, and the index reads its set from the joined tables.
    tables = panorama_to_terraform.join_results([part.parser.parse_associations() for part in parts])
    index = api_requests.scope_index(args.host, tables, lists_read(parts))
    for entry in index:
        if any(part.request.path == entry.path for part in parts):
            continue    # one response is read once, so a container already read as its membership response
                        # is not read again for its index entry
        part = read_part(args, entry.path, producer)
        if part is not None:
            parts.append(part)
    return parts, index


def run(argv, producer=None) -> int:
    """One path 2 run: the arguments, the order, the reference sources, and the run sequence (rule 4).

    `producer` is the injected producer the pins use, so a test run reads the committed response set without
    calling a network (criterion 10). A run that names no producer reads the network producer, as path 1 does.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.host:
        parser.error('--host is needed: the request set is the scope set, and a request names no host '
                     'without one')
    panorama_to_terraform.shared_checks(parser, args)
    scopes = panorama_to_terraform.data_scopes(parser, args)

    try:
        parts, index = run_order(args, producer)

        # F5.6: the state document is a reference source, read last, so its record is last. It is read as a
        # file, so no producer is called for it and no part enters the run order.
        state_source = None
        if args.state:
            print(panorama_to_terraform.state_line(args.state, args.workspace))
            state_source = state_input.read_state(args.state, workspace=args.workspace,
                                                   max_input_bytes=args.max_input_bytes)

        view = entry_coverage.RunView(parts, panorama_to_terraform.join_results)
        return panorama_to_terraform.generate_run(args, view, scopes, index=index,
                                                   state_source=state_source, entry_point=ENTRY_POINT)

    except Exception as e:
        # Both shapes are stated in the module that owns the exit codes, so this entry point prints no line of
        # its own (rule 4, and criterion 7).
        if panorama_to_terraform.is_refusal(e):
            # The read name is the host the run read, because a path 2 run names no input file (criterion 5).
            return panorama_to_terraform.refused(args.host, e)
        return panorama_to_terraform.failed(e)


def main():
    """Path 2's entry point: the arguments, the run order, and the run sequence (criterion 3)."""
    sys.exit(run(sys.argv[1:]))


if __name__ == '__main__':
    main()
