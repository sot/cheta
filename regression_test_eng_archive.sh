export ENG_ARCHIVE=$PWD/test/eng_archive

mkdir -p test/eng_archive
rm -rf test/eng_archive/*
cp /proj/sot/ska/data/eng_archive/filetypes*.dat test/eng_archive/
mkdir test/eng_archive/data

rm -f test/make_eng_archive.log
touch test/make_eng_archive.log

CONTENTS="--content=acis2eng --content=acis3eng --content=acisdeahk --content=ccdm4eng --content=simcoor --content=thm1eng --content=orbitephem0"
DATAROOT="--data-root=$PWD/test/eng_archive"

echo "Updating archive, do 'tail -f test/make_eng_archive.log' in another window"

python -m cheta.update_archive $DATAROOT $CONTENTS --date-now=2024:005 --date-start=2024:001 --max-lookback-time=5 --create >> test/make_eng_archive.log 2>&1
python -m cheta.update_archive $DATAROOT $CONTENTS --date-now=2024:007 >> test/make_eng_archive.log 2>&1
python -m cheta.update_archive $DATAROOT $CONTENTS --date-now=2024:011 >> test/make_eng_archive.log 2>&1
python -m cheta.update_archive $DATAROOT $CONTENTS --date-now=2024:015 >> test/make_eng_archive.log 2>&1

python -m cheta.add_derived $DATAROOT --content=dp_acispow --start=2024:001 --stop=2024:002 >> test/make_eng_archive.log 2>&1
python -m cheta.update_archive $DATAROOT --content=dp_acispow128 --date-now=2024:005 --date-start=2024:001 --max-lookback-time=5 >> test/make_eng_archive.log 2>&1
python -m cheta.update_archive $DATAROOT --content=dp_acispow128 --date-now=2024:007 >> test/make_eng_archive.log 2>&1
python -m cheta.update_archive $DATAROOT --content=dp_acispow128 --date-now=2024:011 >> test/make_eng_archive.log 2>&1
python -m cheta.update_archive $DATAROOT --content=dp_acispow128 --date-now=2024:015 >> test/make_eng_archive.log 2>&1


unset ENG_ARCHIVE

cd test
  ./get_regr_vals.py --start 2024:002 --stop 2024:008
  ./get_regr_vals.py --start 2024:002 --stop 2024:008 --test
  ./compare_regr_vals.py
cd ..
