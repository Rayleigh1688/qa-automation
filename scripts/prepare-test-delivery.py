#!/usr/bin/env python3
"""Prepare API/manual team views or import manual evidence. Entirely offline."""
import argparse
from pathlib import Path
from qa_core.team_delivery import prepare, import_results, DeliveryError
from qa_core.execution_plan import load

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare')
    p.add_argument('story');p.add_argument('--out',type=Path,required=True)
    p.add_argument('--environment',default='FAT');p.add_argument('--version',default='未提供')
    p.add_argument('--extra-views',action='store_true')
    p=sub.add_parser('import')
    p.add_argument('--packet',type=Path,required=True);p.add_argument('--manual',type=Path,required=True)
    p.add_argument('--auto-results',type=Path,action='append',default=[]);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--extra-views',action='store_true')
    args=parser.parse_args()
    if args.command=='prepare':
        import re
        if not re.fullmatch(r'ISOP-\d+',args.story): raise ValueError('invalid story')
        from filbet.requirement_adapter import METHODS
        plan,cases,digest=load(ROOT/'requirements'/args.story/'plan.json',METHODS)
        result=prepare(plan,cases,digest,args.out,args.environment,args.version,extra_views=args.extra_views)
        if args.story=='ISOP-2027':
            from filbet.requirement_kyc import png_bytes
            sample_dir=args.out/'samples';sample_dir.mkdir()
            for size in [256,512000,512001]:
                (sample_dir/(str(size)+'.png')).write_bytes(png_bytes(size))
        print('Packet:',result['packet_id'],'manual:',len(result['manual_rows']),'no login')
    else:
        import_results(args.packet,args.manual,args.out,args.auto_results,extra_views=args.extra_views)
        print('Evidence imported; no tests executed; latest real-run pointer unchanged')
    print(args.out/'results.html')
    return 0


if __name__=='__main__':
    try: raise SystemExit(main())
    except DeliveryError as error:
        print('Delivery validation failed:',str(error))
        raise SystemExit(1)
    except (ValueError,KeyError,OSError):
        print('Delivery validation failed; check schema, fixed columns, provenance and evidence. No report was accepted.')
        raise SystemExit(1)
