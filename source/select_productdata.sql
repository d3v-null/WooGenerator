SELECT 
    %s
FROM
    `%s` p
    INNER JOIN `%s` pm
    ON p.`ID` = pm.`post_id`
WHERE
    p.`post_type` = 'product'
    AND p.`post_status` = 'publish'
GROUP BY
    p.`ID`
    