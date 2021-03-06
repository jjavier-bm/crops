# -*- coding: utf-8 -*-

"""==========
This script will remove a number of residues from a sequence file
in agreement to the intervals and other details supplied.

"""

from crops.about import __prog__, __description__, __author__, __date__, __version__

import argparse
import os
#import copy
from warnings import warn

from crops.core import cio
from crops.core import ops as cop
#from core import seq as csq

import time

def main():
    starttime=time.time()
    parser = argparse.ArgumentParser(prog=__prog__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=__description__+' ('+__prog__+')  v.'+__version__+'\n'+__doc__)
    parser.add_argument("input_seqpath",nargs=1, metavar="Sequence_filepath",
                        help="Input sequence filepath.")
    parser.add_argument("input_database",nargs=1, metavar="Intervals_database",
                        help="Input intervals database filepath.")

    parser.add_argument("-o","--outdir",nargs=1,metavar="Output_Directory",
                        help="Set output directory path. If not supplied, default is the one containing the input sequence.")

    parser.add_argument("-s","--sort",nargs=1, metavar="Sort_type",
                        help="Sort output sequences in descending order by criteria provided - 'ncrops' or 'percent'. Add 'T' ('ncropsIN', 'percentIN') to ignore numbers from terminals. Only for multiple ID fasta inputs.")

    sections=parser.add_mutually_exclusive_group(required=False)
    sections.add_argument("-t","--terminals",action='store_true',default=False,
                          help="Ignore interval discontinuities and only crop the ends off.")
    sections.add_argument("-u","--uniprot_threshold", nargs=2, metavar=("Uniprot_ratio_threshold","Sequence_database"),
                          help='Act if SIFTS database is used as intervals source AND %% residues from single Uniprot sequence is above threshold. [MIN,MAX)=[0,100) uniprot_sprot.fasta-path')
    parser.add_argument('--version', action='version', version='%(prog)s '+ __version__)

    args = parser.parse_args()

    inseq=cio.check_path(args.input_seqpath[0],'file')
    indb=cio.check_path(args.input_database[0],'file')
    insprot=cio.check_path(args.uniprot_threshold[1]) if args.uniprot_threshold is not None else None

    minlen=float(args.uniprot_threshold[0]) if args.uniprot_threshold is not None else 0.0
    targetlbl=cio.target_format(indb,terms=args.terminals, th=minlen)
    infixlbl=cio.infix_gen(indb,terms=args.terminals)

    if args.outdir is None:
        outdir=cio.check_path(os.path.dirname(inseq),'dir')
    else:
        outdir=cio.check_path(os.path.join(args.outdir[0],''),'dir')

    if args.sort is not None:
        if (args.sort[0].lower()!='ncrops' and args.sort[0].lower()!='percent' and
            args.sort[0].lower()!='ncropsin' and args.sort[0].lower()!='percentin'):
            raise ValueError("Arguments for sorting option can only be either 'ncrops' or 'percent'.")
        else:
            sorter=args.sort[0].lower()

    ###########################################

    seqset=cio.parseseqfile(inseq)
    if len(seqset)>0:
        intervals=cio.import_db(indb,pdb_in=seqset)
    else:
        raise ValueError('No chains were imported from sequence file.')

    if insprot is not None and minlen>0.0:
        uniprotset={}
        for seqncid, seqnc in seqset.items():
            for monomerid, monomer in seqnc.imer.items():
                if 'uniprot' in intervals[seqncid][monomerid].tags:
                    for key in intervals[seqncid][monomerid].tags['uniprot']:
                        if key.upper() not in uniprotset:
                            uniprotset[key.upper()]=None

        uniprotset=cio.parseseqfile(insprot, uniprot=uniprotset)['uniprot']

    if len(seqset)>1 and args.sort is not None:
        sorted_outseq={}

    for key, S in seqset.items():
        if key in intervals:
            for key2,monomer in S.imer.items():
                if key2 in intervals[key]:
                    if insprot is not None and minlen>0.0:
                        newinterval=intervals[key][key2].deepcopy()
                        newinterval.tags['description']+=' - Uniprot threshold'
                        newinterval.subint=[]
                        unilbl=' uniprot chains included: '
                        for unicode,uniintervals in intervals[key][key2].tags['uniprot'].items():
                            if 100*uniintervals.n_elements()/uniprotset.imer[unicode].length()>=minlen:
                                newinterval=newinterval.union(intervals[key][key2].intersection(uniintervals))
                                unilbl+=unicode +'|'
                        monomer=cop.crop_seq(monomer,newinterval,targetlbl+unilbl,terms=args.terminals)
                    else:
                        monomer=cop.crop_seq(monomer,intervals[key][key2],targetlbl,terms=args.terminals)
                        if monomer.ncrops()>0:
                            monomer.info['header'] += ' |'
                    if monomer.ncrops()>0:
                        monomer.info['header'] += ' Units cropped: ' + str(monomer.ncrops())
                        monomer.info['header'] += ' (' + str(monomer.ncrops(offmidseq=True))+' not from terminals) '
                        monomer.info['header'] += '; % cropped: '+str(round(100*monomer.ncrops()/len(monomer.seqs['cropseq']),2))
                        monomer.info['header'] += ' (' +str(round(100*monomer.ncrops(offmidseq=True)/len(monomer.seqs['cropseq']),2))+' not from terminals) '

                else:
                    pass
                if len(seqset)==1 or args.sort is None:
                    if len(seqset)>1:
                        outseq=cio.outpath(outdir,filename=os.path.splitext(os.path.basename(inseq))[0]+infixlbl["crop"]+os.path.splitext(os.path.basename(inseq))[1])
                    else:
                        outseq=cio.outpath(outdir,subdir=key,filename=key+infixlbl["crop"]+os.path.splitext(os.path.basename(inseq))[1],mksubdir=True)
                    monomer.dump(outseq)
                if len(seqset)>1 and args.sort is not None:
                    sorted_outseq[monomer.info['oligomer_id']+'_'+monomer.info['chain_id']]=monomer.deepcopy()
        else:
            for key2,monomer in S.imer.items():
                if len(seqset)==1 or args.sort is None:
                    if len(seqset)>1:
                        outseq=cio.outpath(outdir,filename=os.path.splitext(os.path.basename(inseq))[0]+infixlbl["crop"]+os.path.splitext(os.path.basename(inseq))[1])
                    else:
                        outseq=cio.outpath(outdir,subdir=key,filename=key+infixlbl["crop"]+os.path.splitext(os.path.basename(inseq))[1],mksubdir=True)
                    monomer.dump(outseq)
                if len(seqset)>1 and args.sort is not None:
                    sorted_outseq[monomer.info['oligomer_id']+'_'+monomer.info['chain_id']]=monomer.deepcopy()
    croptime=time.time()
    print('Crop time = '+str(croptime-starttime)+ ' s')

    if len(seqset)>1 and args.sort is not None:
        outseq=cio.outpath(outdir,filename=os.path.splitext(os.path.basename(inseq))[0]+infixlbl["crop"]+".sorted_"+sorter+os.path.splitext(os.path.basename(inseq))[1])
        if sorter=='ncrops':
            sorted_outseq2=sorted(sorted_outseq.items(), key=lambda x: x[1].ncrops(),reverse=True)
        elif sorter=='percent':
            sorted_outseq2=sorted(sorted_outseq.items(), key=lambda x: x[1].ncrops()/x[1].full_length(), reverse=True)
        elif sorter=='ncropsin':
            sorted_outseq2=sorted(sorted_outseq.items(), key=lambda x: x[1].ncrops(offmidseq=True),reverse=True)
        elif sorter=='percentin':
            sorted_outseq2=sorted(sorted_outseq.items(), key=lambda x: x[1].ncrops(offmidseq=True)/x[1].full_length(), reverse=True)
        del sorted_outseq
        for monomer in sorted_outseq2:
            monomer[1].dump(outseq)
        print('Sort time = '+str(time.time()-croptime)+ ' s')

if __name__ == "__main__":
    import sys
    #import traceback

    try:
        main()
        sys.exit(0)
    except:
        sys.exit(1)
    #except Exception as e:
    #    if not isinstance(e, SystemExit):
    #        msg = "".join(traceback.format_exception(*sys.exc_info()))
    #        logger.critical(msg)
    #    sys.exit(1)
