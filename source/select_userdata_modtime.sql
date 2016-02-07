SELECT *
FROM (
    (    
        SELECT  
            %s
        FROM
            %s u
            LEFT JOIN %s um
            ON ( um.`user_id` = u.`ID`)
        GROUP BY
           u.`ID`
    ) as ud
    LEFT JOIN (
        SELECT
            tu.`user_id` as `user_id`,
            MAX(tu.`time`) as `updated`
        FROM
            %s tu
        GROUP BY 
            tu.`user_id`
    ) as lu
    ON (ud.`Wordpress ID` = lu.`user_id`)
) ;