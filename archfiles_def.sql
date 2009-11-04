CREATE TABLE archfiles (
  filename        text not null,
  filetime        int  not null,
  year            int not null,
  doy             int not null,
  tstart          float not null,
  tstop           float not null,
  rowstart        int not null,
  rowstop         int not null,
  startmjf        int not null,
  startmnf        int not null,
  stopmjf         int not null,
  stopmnf         int not null,
  checksum        text not null,
  tlmver          text not null,
  ascdsver        text not null,
  revision        int not null,
  date            text not null,

  CONSTRAINT pk_archfiles PRIMARY KEY (filename)
);

CREATE INDEX idx_archfiles_filetime ON archfiles (filetime);
