CREATE TABLE `laptop`
  (
     `id`            INT(5) NOT NULL auto_increment,
     `manufacturer`  VARCHAR(40) NOT NULL,
     `screen_size`   INT(3) NULL,
     `screen_width`  INT(5) NULL,
     `screen_height` INT(5) NULL,
     `matrix_type`   ENUM('matowa','blyszczaca') NULL,
     `is_touch`      BOOLEAN NOT NULL,
     `cpu`           VARCHAR(40) NULL,
     `cpu_cores`     INT(3) NULL,
     `cpu_clock`     INT(6) NULL,
     `ram`           INT(4) NULL,
     `disk_space`    INT(7) NULL,
     `disk_type`     ENUM('HDD','SSD') NULL,
     `gpu`           VARCHAR(40) NULL,
     `gpu_mem`       INT(4) NULL,
     `os`            VARCHAR(40) NULL,
     `odd`           ENUM('DVD','Blu-Ray','brak') NULL,
     PRIMARY KEY (`id`)
  )
engine = innodb;